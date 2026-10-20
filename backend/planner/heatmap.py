"""Heatmap corridor: a coarse grid of weather cells around the routes, with the
composite risk level at every hour from departure (hour 0) to +48 h.

Heatmap cells are every STEP weather cells (0.5 degrees, ~35 mi), so the
corridor stays a few hundred points even on a cross-country trip.
"""

import math
from datetime import datetime, timedelta

from .risk import assess
from .weather import GRID, HEATMAP_HOURS, WeatherError, conditions_at

STEP = 5  # weather cells per heatmap cell


def corridor(routes_coords) -> set[tuple[int, int]]:
    """Heatmap cells (in weather-grid units) along every route, plus one cell either side."""
    cells = set()
    for coords in routes_coords:
        for (lon0, lat0), (lon1, lat1) in zip(coords, coords[1:]):
            # Sample long straight segments at least twice per heatmap cell so none are skipped.
            n = max(1, math.ceil(max(abs(lon1 - lon0), abs(lat1 - lat0)) * GRID / STEP * 2))
            for k in range(n + 1):
                hx = round((lon0 + (lon1 - lon0) * k / n) * GRID / STEP)
                hy = round((lat0 + (lat1 - lat0) * k / n) * GRID / STEP)
                cells.update(((hx + dx) * STEP, (hy + dy) * STEP) for dx in (-1, 0, 1) for dy in (-1, 0, 1))
    return cells


def risk_matrix(cells, series: dict, departure: datetime, weight_lb: float) -> dict:
    """{"points": [[lon, lat]], "risk": [[level per hour 0..48]]}, rows aligned with points."""
    points, risk = [], []
    for cell in sorted(cells):
        try:
            row = []
            for h in range(HEATMAP_HOURS + 1):
                wx = conditions_at(series[cell], departure + timedelta(hours=h))
                row.append(int(assess(wx.wind_mph, wx.rain_in_hr, wx.snow_in_hr, weight_lb).overall))
        except WeatherError:
            continue  # a cell with gaps in its forecast is left off the map rather than failing the plan
        points.append([cell[0] / GRID, cell[1] / GRID])
        risk.append(row)
    return {"points": points, "risk": risk}
