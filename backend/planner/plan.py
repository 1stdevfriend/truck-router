"""Build a trip plan: routes -> checkpoints -> weather -> risk -> ranking.

Ranking (best first): fewest No-Travel miles, then the spec's order —
fewest Severe miles, fewest High miles, lowest average risk, shortest time.
"""

from dataclasses import dataclass
from datetime import datetime

from . import ors, weather
from .risk import Risk, assess
from .sampling import sample_checkpoints

CRITERIA = (
    # (label, key on a scored route, unit) — order is the ranking order
    ("No-Travel miles", "no_travel_miles", "mi"),
    ("Severe miles", "severe_miles", "mi"),
    ("High miles", "high_miles", "mi"),
    ("average risk", "avg_risk", ""),
    ("travel time", "duration_h", "h"),
)


def level_name(level: Risk) -> str:
    return level.name.lower()


@dataclass
class Scored:
    route: ors.Route
    checkpoints: list  # dicts ready for JSON
    miles: dict  # level name -> miles

    @property
    def no_travel_miles(self):
        return round(self.miles["no_travel"], 1)

    @property
    def severe_miles(self):
        return round(self.miles["severe"], 1)

    @property
    def high_miles(self):
        return round(self.miles["high"], 1)

    @property
    def avg_risk(self):
        """Mile-weighted mean level, 0 (Low) to 4 (No Travel)."""
        total = sum(self.miles.values())
        weighted = sum(Risk[name.upper()] * mi for name, mi in self.miles.items())
        return round(weighted / total, 2) if total else 0.0

    @property
    def duration_h(self):
        return round(self.route.duration_s / 3600, 2)

    def rank_key(self):
        return tuple(getattr(self, key) for _, key, _ in CRITERIA)


def score_route(route, sampled, series, weight_lb) -> Scored:
    miles = {level_name(r): 0.0 for r in Risk}
    checkpoints = []
    for cp in sampled:
        wx = weather.conditions_at(series[weather.cell_of(cp.lon, cp.lat)], cp.eta)
        risk = assess(wx.wind_mph, wx.rain_in_hr, wx.snow_in_hr, weight_lb)
        miles[level_name(risk.overall)] += cp.segment_miles
        checkpoints.append(
            {
                "mile": cp.mile,
                "lon": round(cp.lon, 5),
                "lat": round(cp.lat, 5),
                "eta": cp.eta.replace(microsecond=0).isoformat(),
                "segment_miles": cp.segment_miles,
                "wind_mph": wx.wind_mph,
                "gust_mph": wx.gust_mph,
                "rain_in_hr": wx.rain_in_hr,
                "snow_in_hr": wx.snow_in_hr,
                "risk": level_name(risk.overall),
                "risk_by": {"wind": level_name(risk.wind), "rain": level_name(risk.rain), "snow": level_name(risk.snow)},
            }
        )
    return Scored(route, checkpoints, miles)


def explain(best: Scored, runner_up: Scored | None) -> str:
    """Why `best` beat the next route: the first ranking criterion that differs."""
    if runner_up is None:
        return "Only one route was found."
    for label, key, unit in CRITERIA:
        a, b = getattr(best, key), getattr(runner_up, key)
        if a != b:
            return f"Lowest {label}: {a:g}{unit} vs {b:g}{unit} on the next-best route."
    return "All routes tie on risk and time; the first is shown."


def build_plan(origin, destination, departure: datetime, weight_lb: float, interval_mi: int) -> dict:
    routes = ors.get_routes(origin, destination, weight_lb)

    # One weather fetch for every checkpoint on every route.
    sampled = [sample_checkpoints(r, interval_mi, departure) for r in routes]
    start, end = weather.forecast_window(departure, max(cps[-1].eta for cps in sampled))
    cells = {weather.cell_of(cp.lon, cp.lat) for cps in sampled for cp in cps}
    series = weather.fetch(cells, start, end)

    scored = [score_route(r, cps, series, weight_lb) for r, cps in zip(routes, sampled)]
    order = sorted(range(len(scored)), key=lambda i: scored[i].rank_key())
    best = order[0]

    warnings = []
    if all(s.no_travel_miles > 0 for s in scored):
        warnings.append("Every route crosses No-Travel conditions. Consider delaying departure.")
    elif scored[best].severe_miles > 0:
        warnings.append(f"The recommended route still has {scored[best].severe_miles:g} Severe miles.")

    return {
        "departure": departure.isoformat(),
        "interval_mi": interval_mi,
        "weight_lb": weight_lb,
        "recommended": best,
        "ranking": order,
        "reason": explain(scored[best], scored[order[1]] if len(order) > 1 else None),
        "warnings": warnings,
        "routes": [
            {
                "id": i,
                "label": f"Route {chr(65 + i)}",
                "source": s.route.source,
                "distance_mi": round(s.route.distance_m / 1609.344, 1),
                "duration_h": s.duration_h,
                "arrival": s.checkpoints[-1]["eta"],
                "miles_by_level": {k: round(v, 1) for k, v in s.miles.items()},
                "avg_risk": s.avg_risk,
                "max_risk": max((c["risk"] for c in s.checkpoints), key=lambda n: Risk[n.upper()]),
                "geometry": [[round(lon, 5), round(lat, 5)] for lon, lat in s.route.coords],
                "checkpoints": s.checkpoints,
            }
            for i, s in enumerate(scored)
        ],
    }
