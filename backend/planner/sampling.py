"""Weather checkpoints every N road-miles along a route, with the truck's ETA at each.

Each checkpoint stands for the stretch of road that ends at it, so
`segment_miles` is how many miles its weather risk counts for.
"""

from bisect import bisect_left
from dataclasses import dataclass
from datetime import datetime, timedelta

from .geo import METERS_PER_MILE, haversine_m
from .ors import Route, Step


@dataclass(frozen=True)
class Checkpoint:
    mile: float
    lon: float
    lat: float
    eta: datetime
    segment_miles: float


def _vertex_profile(route: Route) -> tuple[list[float], list[float]]:
    """Cumulative road miles and elapsed seconds at every route vertex."""
    coords = route.coords
    legs = [haversine_m(coords[i], coords[i + 1]) for i in range(len(coords) - 1)]
    total_m = sum(legs)
    # Polyline length is within ~1% of ORS's distance; scale so totals match the route summary.
    scale = route.distance_m / total_m if total_m and route.distance_m else 1.0

    # ORS steps give a duration per stretch of vertices; spread it by length within the step.
    steps = route.steps or [Step(route.distance_m, route.duration_s, 0, len(coords) - 1)]
    leg_seconds = [0.0] * len(legs)
    for step in steps:
        step_m = sum(legs[step.start : step.end])
        for i in range(step.start, step.end):
            leg_seconds[i] = step.duration_s * legs[i] / step_m if step_m else 0.0

    miles, seconds = [0.0], [0.0]
    for leg_m, leg_s in zip(legs, leg_seconds):
        miles.append(miles[-1] + leg_m * scale / METERS_PER_MILE)
        seconds.append(seconds[-1] + leg_s)
    return miles, seconds


def sample_checkpoints(route: Route, interval_mi: float, departure: datetime) -> list[Checkpoint]:
    miles, seconds = _vertex_profile(route)
    total = miles[-1]
    targets = [interval_mi * k for k in range(1, int(total // interval_mi) + 1) if interval_mi * k < total] + [total]

    checkpoints, prev = [], 0.0
    for target in targets:
        i = max(1, bisect_left(miles, target))  # vertex i is the first at/after target
        span = miles[i] - miles[i - 1]
        f = (target - miles[i - 1]) / span if span else 0.0
        (lon0, lat0), (lon1, lat1) = route.coords[i - 1], route.coords[i]
        elapsed = seconds[i - 1] + f * (seconds[i] - seconds[i - 1])
        checkpoints.append(
            Checkpoint(
                mile=round(target, 2),
                lon=lon0 + f * (lon1 - lon0),
                lat=lat0 + f * (lat1 - lat0),
                eta=departure + timedelta(seconds=elapsed),
                segment_miles=round(target - prev, 2),
            )
        )
        prev = target
    return checkpoints
