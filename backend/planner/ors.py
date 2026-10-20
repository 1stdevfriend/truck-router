"""OpenRouteService client: address autocomplete and 3 distinct truck routes.

ORS's native `alternative_routes` is unreliable on the public API (it often
times out, even on short HGV trips), so it runs alongside a few variant
requests; whichever succeed are pooled and the 3 most distinct are kept.
"""

import hashlib
import logging
import math
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

import requests
from django.conf import settings
from django.core.cache import cache

from .geo import haversine_m

log = logging.getLogger(__name__)

BASE_URL = "https://api.openrouteservice.org"
TIMEOUT = (5, 30)  # connect, read seconds
# ponytail: the form asks for load weight only; assume a typical empty tractor-trailer for the gross-weight restriction.
TARE_LB = 35_000
LB_PER_TONNE = 2204.62
ROUTE_COUNT = 3
CELL_DEG = 0.02  # ~2 km grid used to compare corridors
# ORS only computes alternatives for routes under 100 km; road distance runs ~1.2-1.4x straight-line.
ALTERNATIVES_MAX_STRAIGHT_M = 70_000
MAX_CONCURRENT = 3  # ORS public API degrades with many parallel requests from one key
MAX_OVERLAP = 0.8  # routes sharing more than this many corridor cells count as the same


def _cache_key(*parts) -> str:
    return "ors:" + hashlib.sha1(repr(parts).encode()).hexdigest()


# ORS error codes a user can cause, reworded; anything else passes through as-is.
PLAIN_ERRORS = {
    2004: "That trip is too long to route. Truck routes are limited to about 3,700 miles.",
    2009: "No truck route connects these two places.",
    2010: "One of the places isn't near a road. Pick a street address or town instead.",
}


class ORSError(Exception):
    pass


@dataclass(frozen=True)
class Step:
    distance_m: float
    duration_s: float
    start: int  # index into Route.coords
    end: int


@dataclass(frozen=True)
class Route:
    source: str  # which request produced it, for debugging
    coords: list  # [[lon, lat], ...]
    distance_m: float
    duration_s: float
    steps: list


def _get(path, params, timeout=TIMEOUT):
    return _call("get", path, timeout, params=params)


def _call(method, path, timeout, **kwargs):
    try:
        res = requests.request(
            method, BASE_URL + path, headers={"Authorization": settings.ORS_API_KEY}, timeout=timeout, **kwargs
        )
    except requests.RequestException as exc:
        raise ORSError(f"Routing service unreachable: {exc.__class__.__name__}") from exc
    if res.status_code != 200:
        try:
            error = res.json()["error"]
            code, message = error.get("code"), error["message"]
        except (ValueError, KeyError, TypeError, AttributeError):
            code, message = None, f"HTTP {res.status_code}"
        raise ORSError(PLAIN_ERRORS.get(code, f"Routing service error: {message}"))
    return res.json()


def autocomplete(text: str) -> list[dict]:
    key = _cache_key("ac", text.lower())
    if (hit := cache.get(key)) is not None:
        return hit
    data = _get("/geocode/autocomplete", {"text": text, "boundary.country": "US", "size": 6}, timeout=(5, 10))
    places = [
        {"label": f["properties"]["label"], "lon": f["geometry"]["coordinates"][0], "lat": f["geometry"]["coordinates"][1]}
        for f in data.get("features", [])
    ]
    cache.set(key, places, 60 * 60 * 24)
    return places


def _parse(data: dict, source: str) -> list[Route]:
    routes = []
    for i, f in enumerate(data.get("features", [])):
        props = f["properties"]
        steps = [
            Step(s["distance"], s["duration"], s["way_points"][0], s["way_points"][1])
            for seg in props.get("segments", [])
            for s in seg.get("steps", [])
        ]
        summary = props.get("summary", {})
        routes.append(
            Route(
                source=f"{source} {i + 1}" if i else source,
                coords=f["geometry"]["coordinates"],
                distance_m=summary.get("distance", 0.0),
                duration_s=summary.get("duration", 0.0),
                steps=steps,
            )
        )
    return routes


def _directions(coords, weight_lb, source, extra=None, avoid=None) -> list[Route]:
    options = {
        "vehicle_type": "hgv",
        "profile_params": {"restrictions": {"weight": round((weight_lb + TARE_LB) / LB_PER_TONNE, 1)}},
    }
    if avoid:
        options["avoid_features"] = avoid
    body = {"coordinates": coords, "radiuses": [-1] * len(coords), "options": options, **(extra or {})}
    return _parse(_call("post", "/v2/directions/driving-hgv/geojson", TIMEOUT, json=body), source)


def detour_point(start, end, side: int, fraction=0.15):
    """A point beside the trip midpoint, offset perpendicular by `fraction` of the trip length."""
    (lon1, lat1), (lon2, lat2) = start, end
    k = math.cos(math.radians((lat1 + lat2) / 2))  # shrink longitude so the offset is perpendicular on the ground
    dx, dy = (lon2 - lon1) * k, lat2 - lat1
    return [(lon1 + lon2) / 2 - side * dy * fraction / k, (lat1 + lat2) / 2 + side * dx * fraction]


def _cells(route: Route) -> set:
    return {(round(lon / CELL_DEG), round(lat / CELL_DEG)) for lon, lat in route.coords}


def overlap(a: set, b: set) -> float:
    return len(a & b) / min(len(a), len(b)) if a and b else 1.0


def pick_distinct(candidates: list[Route], n=ROUTE_COUNT) -> list[Route]:
    """Fastest first, then each next-fastest route that is a different corridor.

    If fewer than n distinct corridors exist, fill with the least-overlapping
    leftovers, but never with a near-identical copy.
    """
    ranked = sorted(candidates, key=lambda r: r.duration_s)
    cells = {id(r): _cells(r) for r in ranked}

    def worst_overlap(r, picked):
        return max((overlap(cells[id(r)], cells[id(p)]) for p in picked), default=0.0)

    picked = []
    for r in ranked:
        if len(picked) < n and worst_overlap(r, picked) < MAX_OVERLAP:
            picked.append(r)
    leftovers = sorted((r for r in ranked if r not in picked), key=lambda r: worst_overlap(r, picked))
    for r in leftovers:
        if len(picked) < n and worst_overlap(r, picked) < 0.98:
            picked.append(r)
    return sorted(picked, key=lambda r: r.duration_s)


def get_routes(start, end, weight_lb) -> list[Route]:
    """Up to 3 distinct HGV routes between [lon, lat] points, fastest first."""
    key = _cache_key("routes", start, end, weight_lb)
    if (hit := cache.get(key)) is not None:
        return hit

    requests_ = [
        ("Fastest", [start, end], {}, None),
        ("Shortest", [start, end], {"preference": "shortest"}, None),
        ("No tolls", [start, end], {}, ["tollways"]),
        ("Detour left", [start, detour_point(start, end, 1), end], {}, None),
        ("Detour right", [start, detour_point(start, end, -1), end], {}, None),
    ]
    if haversine_m(start, end) <= ALTERNATIVES_MAX_STRAIGHT_M:
        # last: it is the request most likely to hang, so it shouldn't hold a worker the others need
        alternatives = {"alternative_routes": {"target_count": 3, "weight_factor": 1.6, "share_factor": 0.6}}
        requests_.append(("Alternative", [start, end], alternatives, None))

    def run(req):
        source, coords, extra, avoid = req
        try:
            return _directions(coords, weight_lb, source, extra, avoid), None
        except ORSError as exc:
            log.warning("ORS %s request failed: %s", source, exc)
            return [], exc

    with ThreadPoolExecutor(max_workers=MAX_CONCURRENT) as pool:
        results = list(pool.map(run, requests_))

    candidates = [r for routes, _ in results for r in routes]
    if not candidates:
        raise results[0][1]  # the plain request's error explains it best (e.g. no route found)

    routes = pick_distinct(candidates)
    cache.set(key, routes, 60 * 60)
    return routes
