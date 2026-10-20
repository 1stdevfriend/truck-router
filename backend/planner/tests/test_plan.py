from datetime import datetime, timedelta, timezone
from unittest import mock

import pytest

from planner import plan as plan_mod
from planner.ors import Route
from planner.plan import Scored, explain

LEVELS = ("low", "moderate", "high", "severe", "no_travel")


def scored(duration_h=10, **miles):
    route = Route("x", [[0, 0], [1, 0]], 1000, duration_h * 3600, [])
    return Scored(route, [], {lvl: float(miles.get(lvl, 0)) for lvl in LEVELS})


def best_of(*routes):
    return min(routes, key=lambda s: s.rank_key())


def test_no_travel_miles_rank_before_everything():
    clean_but_severe = scored(low=50, severe=50)
    tiny_no_travel = scored(low=99, no_travel=1)
    assert best_of(tiny_no_travel, clean_but_severe) is clean_but_severe


def test_fewest_severe_then_high_miles():
    a = scored(low=80, severe=10, high=10)
    b = scored(low=70, severe=5, high=25)
    assert best_of(a, b) is b
    c = scored(low=90, high=10)
    d = scored(low=95, high=5, moderate=0)
    assert best_of(c, d) is d


def test_lower_average_risk_then_shorter_time():
    calmer = scored(duration_h=12, low=90, moderate=10)
    windier = scored(duration_h=9, low=50, moderate=50)
    assert best_of(windier, calmer) is calmer
    slow = scored(duration_h=12, low=100)
    fast = scored(duration_h=9, low=100)
    assert best_of(slow, fast) is fast


def test_average_risk_is_mile_weighted():
    assert scored(low=75, high=25).avg_risk == 0.5  # (0*75 + 2*25) / 100


def test_explain_names_the_deciding_criterion():
    assert explain(scored(low=100), scored(low=90, severe=10)).startswith("Lowest Severe miles: 0mi vs 10mi")
    assert "travel time" in explain(scored(duration_h=9, low=100), scored(duration_h=12, low=100))
    assert explain(scored(low=1), None) == "Only one route was found."


# ---- build_plan / endpoint with routes and weather mocked ----

DEPART = datetime.now(timezone.utc).replace(microsecond=0) + timedelta(hours=1)


def east_west(source, lat, hours):
    coords = [[-100 + i * 0.1, lat] for i in range(51)]  # ~5 degrees east
    return Route(source, coords, 450_000, hours * 3600, [])


def fake_fetch(cells, start, end):
    """Calm everywhere except a 50 mph wind band along latitude 35."""
    hours = int((end - start).total_seconds() // 3600) + 1
    times = [int((start + timedelta(hours=h)).timestamp()) for h in range(hours)]
    out = {}
    for cell in cells:
        wind = 50 if cell[1] == 350 else 5
        out[cell] = {"time": times, "wind": [wind] * hours, "gust": [wind + 10] * hours, "rain": [0.0] * hours, "snow": [0.0] * hours}
    return out


@pytest.fixture
def mocked():
    routes = [east_west("Fastest", 35.0, 5), east_west("Detour", 36.0, 6)]
    with mock.patch.object(plan_mod.ors, "get_routes", return_value=routes), mock.patch.object(
        plan_mod.weather, "fetch", side_effect=fake_fetch
    ):
        yield


def test_build_plan_avoids_windy_corridor_for_heavy_load(mocked):
    p = plan_mod.build_plan([-100, 35], [-95, 35], DEPART, 45_000, 25)
    fast, detour = p["routes"]
    assert fast["max_risk"] == "no_travel"  # 50 mph + >30,000 lb
    assert detour["max_risk"] == "low"
    assert p["recommended"] == 1 and p["ranking"] == [1, 0]
    assert p["reason"].startswith("Lowest No-Travel miles")
    assert fast["miles_by_level"]["no_travel"] == pytest.approx(fast["distance_mi"], abs=0.2)
    cp = fast["checkpoints"][0]
    assert cp["risk_by"] == {"wind": "no_travel", "rain": "low", "snow": "low"}


def test_light_load_same_wind_is_severe_not_no_travel(mocked):
    p = plan_mod.build_plan([-100, 35], [-95, 35], DEPART, 20_000, 25)
    assert p["routes"][0]["max_risk"] == "severe"
    assert p["recommended"] == 1


def test_plan_endpoint(client, mocked):
    body = {
        "origin": {"lon": -100, "lat": 35},
        "destination": {"lon": -95, "lat": 35},
        "departure": DEPART.isoformat(),
        "weight_lb": 45000,
        "interval_mi": 50,
    }
    res = client.post("/api/plan", body, content_type="application/json")
    assert res.status_code == 200
    assert res.json()["recommended"] == 1


@pytest.mark.parametrize(
    "change",
    [
        {"interval_mi": 15},
        {"weight_lb": 0},
        {"departure": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()},
        {"destination": {"lon": -100, "lat": 35}},
        {"origin": {"lon": 200, "lat": 35}},
    ],
)
def test_plan_endpoint_rejects_bad_input(client, change):
    body = {
        "origin": {"lon": -100, "lat": 35},
        "destination": {"lon": -95, "lat": 35},
        "departure": DEPART.isoformat(),
        "weight_lb": 45000,
        **change,
    }
    assert client.post("/api/plan", body, content_type="application/json").status_code == 400


def test_upstream_failure_returns_502(client):
    with mock.patch.object(plan_mod.ors, "get_routes", side_effect=plan_mod.ors.ORSError("Routing service unreachable")):
        body = {"origin": {"lon": -100, "lat": 35}, "destination": {"lon": -95, "lat": 35}, "departure": DEPART.isoformat(), "weight_lb": 1}
        res = client.post("/api/plan", body, content_type="application/json")
    assert res.status_code == 502 and "unreachable" in res.json()["error"]
