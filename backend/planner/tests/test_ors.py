from unittest import mock

import pytest

from planner import ors
from planner.ors import Route, detour_point, pick_distinct


def line(source, duration, lat, lon_from=-100.0, lon_to=-90.0, n=200):
    """A straight east-west route at a fixed latitude."""
    step = (lon_to - lon_from) / (n - 1)
    return Route(source, [[lon_from + i * step, lat] for i in range(n)], 1000.0, duration, [])


def test_picks_three_distinct_corridors_fastest_first():
    a = line("a", 100, 35.0)
    a_copy = line("a copy", 101, 35.0)
    b = line("b", 120, 36.0)
    c = line("c", 110, 37.0)
    assert [r.source for r in pick_distinct([b, a_copy, c, a])] == ["a", "c", "b"]


def test_fills_with_partial_overlap_but_never_identical_copies():
    a = line("a", 100, 35.0)
    # shares most of a's corridor but leaves it for the last 10%
    partial = Route("partial", a.coords[:170] + [[lon, 36.0] for lon, _ in a.coords[170:]], 1000, 110, [])
    copy = line("copy", 105, 35.0)
    assert [r.source for r in pick_distinct([a, partial, copy])] == ["a", "partial"]


def test_detour_points_sit_either_side_of_the_midpoint():
    start, end = [-100.0, 35.0], [-90.0, 35.0]  # due east
    north, south = detour_point(start, end, 1), detour_point(start, end, -1)
    assert north[0] == pytest.approx(-95.0) and north[1] > 35.0
    assert south[0] == pytest.approx(-95.0) and south[1] < 35.0


def test_parse_flattens_steps_across_segments():
    data = {
        "features": [
            {
                "geometry": {"coordinates": [[0, 0], [1, 0], [2, 0]]},
                "properties": {
                    "summary": {"distance": 200.0, "duration": 20.0},
                    "segments": [
                        {"steps": [{"distance": 100.0, "duration": 10.0, "way_points": [0, 1]}]},
                        {"steps": [{"distance": 100.0, "duration": 10.0, "way_points": [1, 2]}]},
                    ],
                },
            }
        ]
    }
    (route,) = ors._parse(data, "Fastest")
    assert [(s.start, s.end) for s in route.steps] == [(0, 1), (1, 2)]
    assert route.duration_s == 20.0


def test_get_routes_survives_failed_variants(settings):
    settings.CACHES = {"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}}
    good = [line("x", 100, 35.0)]

    def fake(coords, weight, source, extra=None, avoid=None):
        if source == "Fastest":
            return good
        raise ors.ORSError("timeout")

    with mock.patch.object(ors, "_directions", side_effect=fake):
        assert ors.get_routes([-100, 35], [-90, 35], 40_000) == good


def test_get_routes_raises_when_every_request_fails(settings):
    settings.CACHES = {"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}}
    with mock.patch.object(ors, "_directions", side_effect=ors.ORSError("no route")):
        with pytest.raises(ors.ORSError, match="no route"):
            ors.get_routes([-100, 35], [-90, 35], 40_000)


def test_geocode_validates_query(client):
    assert client.get("/api/geocode?q=a").status_code == 400


def test_alternatives_only_requested_for_short_trips(settings):
    settings.CACHES = {"default": {"BACKEND": "django.core.cache.backends.dummy.DummyCache"}}
    seen = []

    def fake(coords, weight, source, extra=None, avoid=None):
        seen.append(source)
        return [line(source, 100, 35.0)]

    with mock.patch.object(ors, "_directions", side_effect=fake):
        ors.get_routes([-96.80, 32.78], [-87.63, 41.88], 40_000)  # Dallas -> Chicago
        assert "Alternative" not in seen
        seen.clear()
        ors.get_routes([-96.80, 32.78], [-97.33, 32.76], 40_000)  # Dallas -> Fort Worth
        assert "Alternative" in seen
