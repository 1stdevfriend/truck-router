"""Open-Meteo hourly forecasts, fetched in batches for many points at once.

Points are snapped to a 0.1-degree grid (~7 mi, near the forecast models'
own resolution) so nearby checkpoints, overlapping routes and the heatmap
share one cached series per cell.
"""

import logging
import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import requests
from django.core.cache import cache

URL = "https://api.open-meteo.com/v1/forecast"
log = logging.getLogger(__name__)
TIMEOUT = (5, 30)
GRID = 10  # cells per degree
BATCH = 250  # locations per request; keeps the URL ~4 KB
CACHE_SECONDS = 30 * 60
HEATMAP_HOURS = 48
FORECAST_DAYS = 16  # Open-Meteo's forecast horizon
# ponytail: the free tier allows ~10k location-calls/day; caching per cell is the only throttle. Add a paid key if the hosted demo hits the cap.


UNAVAILABLE = "The weather service isn't responding right now. Try again in a few minutes."


class WeatherError(Exception):
    pass


@dataclass(frozen=True)
class Conditions:
    wind_mph: float
    gust_mph: float
    rain_in_hr: float  # rain + showers (liquid)
    snow_in_hr: float


def cell_of(lon: float, lat: float) -> tuple[int, int]:
    return round(lon * GRID), round(lat * GRID)


def forecast_window(departure: datetime, last_eta: datetime) -> tuple[datetime, datetime]:
    """Whole hours covering the trip and the 0–48 h heatmap, so both share cache entries."""
    start = departure.astimezone(timezone.utc).replace(minute=0, second=0, microsecond=0)
    end = max(last_eta.astimezone(timezone.utc), start + timedelta(hours=HEATMAP_HOURS))
    end = end.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    horizon = datetime.now(timezone.utc) + timedelta(days=FORECAST_DAYS)
    if end > horizon:
        raise WeatherError(f"Forecasts only reach {FORECAST_DAYS} days ahead; choose an earlier departure.")
    return start, end


def _cache_key(cell, start, end) -> str:
    return f"wx:{cell[0]}:{cell[1]}:{int(start.timestamp())}:{int(end.timestamp())}"


def _request(cells: list, start: datetime, end: datetime) -> list[dict]:
    params = {
        "longitude": ",".join(f"{lon / GRID:.1f}" for lon, _ in cells),
        "latitude": ",".join(f"{lat / GRID:.1f}" for _, lat in cells),
        "hourly": "wind_speed_10m,wind_gusts_10m,rain,showers,snowfall",
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",  # snowfall also comes back in inches of snow
        "timeformat": "unixtime",
        "timezone": "GMT",
        "start_hour": start.strftime("%Y-%m-%dT%H:%M"),
        "end_hour": end.strftime("%Y-%m-%dT%H:%M"),
    }
    try:
        res = requests.get(URL, params=params, timeout=TIMEOUT)
    except requests.RequestException as exc:
        log.warning("Open-Meteo unreachable (%d locations): %s", len(cells), exc.__class__.__name__)
        raise WeatherError(UNAVAILABLE) from exc
    if res.status_code in (429, 502, 503, 504):
        log.warning("Open-Meteo returned HTTP %s (%d locations): %s", res.status_code, len(cells), res.text[:200])
        raise WeatherError(UNAVAILABLE)
    if res.status_code != 200:
        try:
            reason = res.json()["reason"]
        except (ValueError, KeyError, TypeError):
            reason = f"HTTP {res.status_code}"
        raise WeatherError(f"Weather service error: {reason}")
    data = res.json()
    return data if isinstance(data, list) else [data]  # a single location comes back unwrapped


def fetch(cells, start: datetime, end: datetime) -> dict:
    """Hourly series per cell: {"time": [unix s], "wind", "gust", "rain", "snow": [...]}."""
    cells = sorted(set(cells))
    keys = {c: _cache_key(c, start, end) for c in cells}
    cached = cache.get_many(keys.values())
    out = {c: cached[k] for c, k in keys.items() if k in cached}
    missing = [c for c in cells if c not in out]

    for i in range(0, len(missing), BATCH):
        chunk = missing[i : i + BATCH]
        fresh = {}
        for c, loc in zip(chunk, _request(chunk, start, end)):
            h = loc["hourly"]
            fresh[c] = {
                "time": h["time"],
                "wind": h["wind_speed_10m"],
                "gust": h["wind_gusts_10m"],
                "rain": [_sum(r, s) for r, s in zip(h["rain"], h["showers"])],
                "snow": h["snowfall"],
            }
        cache.set_many({keys[c]: v for c, v in fresh.items()}, CACHE_SECONDS)
        out.update(fresh)
    return out


def _sum(a, b):
    return None if a is None or b is None else a + b


def conditions_at(series: dict, when: datetime) -> Conditions:
    """Weather a truck meets at `when`.

    Wind is an instantaneous value, so use the nearest hour. Rain and snow are
    totals for the hour *ending* at each timestamp, so use the hour whose
    bucket contains `when`.
    """
    t0, times = series["time"][0], series["time"]
    offset_h = (when.timestamp() - t0) / 3600
    nearest, bucket = round(offset_h), math.ceil(offset_h)
    if nearest < 0 or bucket >= len(times):
        raise WeatherError("Checkpoint time is outside the fetched forecast window.")
    values = (series["wind"][nearest], series["gust"][nearest], series["rain"][bucket], series["snow"][bucket])
    if any(v is None for v in values):
        raise WeatherError("Forecast data is missing for part of the trip.")
    return Conditions(*values)
