from datetime import datetime, timedelta, timezone

import pytest

from planner.geo import METERS_PER_MILE, haversine_m
from planner.ors import Route, Step
from planner.sampling import sample_checkpoints

DEPART = datetime(2026, 10, 20, 8, 0, tzinfo=timezone.utc)
COORDS = [[i / 10, 0.0] for i in range(11)]  # 1 degree of longitude along the equator
TOTAL_M = sum(haversine_m(COORDS[i], COORDS[i + 1]) for i in range(10))
TOTAL_MI = TOTAL_M / METERS_PER_MILE  # ~69.1 mi
HALF_MI = TOTAL_MI / 2


def route(steps, distance_m=TOTAL_M, duration_s=5400):
    return Route("test", COORDS, distance_m, duration_s, steps)


# First half driven in 30 min, second half in 60 min.
TWO_SPEEDS = route([Step(TOTAL_M / 2, 1800, 0, 5), Step(TOTAL_M / 2, 3600, 5, 10)])


def test_checkpoints_every_interval_plus_destination():
    cps = sample_checkpoints(TWO_SPEEDS, 10, DEPART)
    assert [round(c.mile) for c in cps] == [10, 20, 30, 40, 50, 60, 69]
    assert cps[-1].segment_miles == pytest.approx(TOTAL_MI - 60, abs=0.01)
    assert sum(c.segment_miles for c in cps) == pytest.approx(TOTAL_MI, abs=0.01)


def test_checkpoint_position_is_interpolated_along_the_line():
    cp = sample_checkpoints(TWO_SPEEDS, 25, DEPART)[0]
    assert cp.lat == pytest.approx(0.0)
    assert cp.lon == pytest.approx(25 / TOTAL_MI, rel=1e-3)


def test_eta_follows_each_steps_speed():
    cps = {round(c.mile): c for c in sample_checkpoints(TWO_SPEEDS, 10, DEPART)}
    # mile 20 is in the fast half: 20/HALF of 1800 s
    assert cps[20].eta == pytest.approx(DEPART + timedelta(seconds=1800 * 20 / HALF_MI), abs=timedelta(seconds=1))
    # mile 40 is in the slow half: 1800 s plus its share of 3600 s
    expected = 1800 + 3600 * (40 - HALF_MI) / HALF_MI
    assert cps[40].eta == pytest.approx(DEPART + timedelta(seconds=expected), abs=timedelta(seconds=1))
    assert cps[69].eta == DEPART + timedelta(seconds=5400)


def test_interval_longer_than_route_gives_destination_only():
    (cp,) = sample_checkpoints(TWO_SPEEDS, 100, DEPART)
    assert cp.segment_miles == pytest.approx(TOTAL_MI, abs=0.01)
    assert (cp.lon, cp.lat) == (1.0, 0.0)


def test_miles_scaled_to_ors_distance_and_no_steps_falls_back_to_even_speed():
    # ORS says the road is 10% longer than the polyline; there are no steps.
    r = route([], distance_m=TOTAL_M * 1.1, duration_s=3600)
    cps = sample_checkpoints(r, 50, DEPART)
    assert cps[-1].mile == pytest.approx(TOTAL_MI * 1.1, abs=0.01)
    assert cps[0].eta == pytest.approx(DEPART + timedelta(seconds=3600 * 50 / (TOTAL_MI * 1.1)), abs=timedelta(seconds=1))
