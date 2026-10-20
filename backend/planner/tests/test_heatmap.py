from datetime import datetime, timedelta, timezone

from planner.heatmap import corridor, risk_matrix

DEPART = datetime(2026, 10, 20, 14, 30, tzinfo=timezone.utc)


def series(hours=50, wind=5, snow_from_hour=None):
    start = DEPART.replace(minute=0)
    snow = [0.0] * hours
    if snow_from_hour is not None:
        snow[snow_from_hour:] = [1.5] * (hours - snow_from_hour)  # High
    return {
        "time": [int((start + timedelta(hours=h)).timestamp()) for h in range(hours)],
        "wind": [wind] * hours,
        "gust": [wind + 5] * hours,
        "rain": [0.0] * hours,
        "snow": snow,
    }


def test_corridor_is_a_3_cell_band_with_no_gaps_on_long_segments():
    cells = corridor([[[-100.0, 35.0], [-98.0, 35.0]]])  # one 2-degree segment, no vertices between
    lons = sorted({c[0] for c in cells})
    assert lons == list(range(-1005, -970, 5))  # -100.5 .. -97.5 every 0.5 degree, nothing skipped
    assert {c[1] for c in cells} == {345, 350, 355}


def test_matrix_has_49_hours_from_departure():
    out = risk_matrix({(-1000, 350)}, {(-1000, 350): series(snow_from_hour=10)}, DEPART, 20_000)
    assert out["points"] == [[-100.0, 35.0]]
    (row,) = out["risk"]
    assert len(row) == 49
    # 14:30 + 9h = 23:30 falls in the bucket labelled 00:00 (index 10)
    assert row[8] == 0 and row[9] == 2


def test_load_weight_applies_to_heatmap_wind():
    cells = {(0, 0)}
    light = risk_matrix(cells, {(0, 0): series(wind=40)}, DEPART, 20_000)
    heavy = risk_matrix(cells, {(0, 0): series(wind=40)}, DEPART, 45_000)
    assert light["risk"][0][0] == 2 and heavy["risk"][0][0] == 3


def test_cell_with_missing_forecast_is_dropped():
    gappy = series()
    gappy["wind"][20] = None
    out = risk_matrix({(0, 0), (5, 0)}, {(0, 0): gappy, (5, 0): series()}, DEPART, 20_000)
    assert out["points"] == [[0.5, 0.0]]
