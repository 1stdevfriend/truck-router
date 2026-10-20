from datetime import datetime, timedelta, timezone
from unittest import mock

import pytest
from django.core.cache import cache

from planner import weather
from planner.weather import Conditions, WeatherError, conditions_at, forecast_window

T0 = datetime(2026, 10, 20, 14, 0, tzinfo=timezone.utc)
SERIES = {
    "time": [int((T0 + timedelta(hours=h)).timestamp()) for h in range(4)],
    "wind": [10, 20, 30, 40],
    "gust": [15, 25, 35, 45],
    "rain": [0.0, 0.1, 0.2, 0.3],  # total for the hour ending at each time
    "snow": [0.0, 0.5, 1.0, 1.5],
}


def at(hours):
    return T0 + timedelta(hours=hours)


def test_wind_uses_nearest_hour_precip_uses_hour_bucket_containing_time():
    # 15:20 -> wind from 15:00 (nearest); precip from the 15:00–16:00 bucket (labelled 16:00)
    assert conditions_at(SERIES, at(1 + 20 / 60)) == Conditions(20, 25, 0.2, 1.0)
    # 15:40 -> wind from 16:00
    assert conditions_at(SERIES, at(1 + 40 / 60)).wind_mph == 30


def test_time_outside_window_or_missing_value_raises():
    with pytest.raises(WeatherError):
        conditions_at(SERIES, at(3.5))
    with pytest.raises(WeatherError):
        conditions_at({**SERIES, "rain": [0, None, 0, 0]}, at(0.5))


def test_window_covers_48h_heatmap_or_whole_trip():
    depart = datetime.now(timezone.utc).replace(microsecond=0) + timedelta(hours=2, minutes=30)
    start, end = forecast_window(depart, depart + timedelta(hours=5))
    assert start == depart.replace(minute=0, second=0)
    assert end == start + timedelta(hours=49)
    _, end = forecast_window(depart, depart + timedelta(hours=60))
    assert end >= depart + timedelta(hours=60)


def test_window_beyond_forecast_horizon_raises():
    far = datetime.now(timezone.utc) + timedelta(days=15)
    with pytest.raises(WeatherError, match="16 days"):
        forecast_window(far, far + timedelta(hours=30))


def fake_location(n_hours=3):
    return {
        "hourly": {
            "time": list(range(n_hours)),
            "wind_speed_10m": [5] * n_hours,
            "wind_gusts_10m": [9] * n_hours,
            "rain": [0.1] * n_hours,
            "showers": [0.05] * n_hours,
            "snowfall": [0.0] * n_hours,
        }
    }


def fake_get(url, params, timeout):
    n = len(params["latitude"].split(","))
    res = mock.Mock(status_code=200)
    res.json.return_value = fake_location() if n == 1 else [fake_location() for _ in range(n)]
    return res


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()


def test_fetch_batches_sums_showers_and_caches():
    cells = [(i, 300) for i in range(weather.BATCH + 10)]
    with mock.patch.object(weather.requests, "get", side_effect=fake_get) as get:
        out = weather.fetch(cells + cells[:5], T0, at(49))  # duplicates collapse
        assert get.call_count == 2
        assert len(out) == len(cells)
        assert out[cells[0]]["rain"][0] == pytest.approx(0.15)
        weather.fetch(cells[:3], T0, at(49))
        assert get.call_count == 2  # all cached


def test_fetch_handles_single_location_response():
    with mock.patch.object(weather.requests, "get", side_effect=fake_get):
        assert list(weather.fetch([(1, 2)], T0, at(49))) == [(1, 2)]


def test_fetch_surfaces_api_reason():
    res = mock.Mock(status_code=400)
    res.json.return_value = {"error": True, "reason": "Parameter start_hour is out of range"}
    with mock.patch.object(weather.requests, "get", return_value=res):
        with pytest.raises(WeatherError, match="out of range"):
            weather.fetch([(1, 2)], T0, at(49))
