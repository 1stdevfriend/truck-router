import pytest

from planner.risk import Risk, assess, rain_risk, snow_risk, wind_risk

L, M, H, S, N = Risk.LOW, Risk.MODERATE, Risk.HIGH, Risk.SEVERE, Risk.NO_TRAVEL
LIGHT = 10_000  # below every load rule


@pytest.mark.parametrize(
    "mph,expected",
    [(0, L), (24.9, L), (25, M), (34.9, M), (35, H), (44.9, H), (45, S), (54.9, S), (55, N), (80, N)],
)
def test_wind_bands_light_load(mph, expected):
    assert wind_risk(mph, LIGHT) == expected


@pytest.mark.parametrize(
    "in_hr,expected",
    [(0, L), (0.09, L), (0.10, M), (0.24, M), (0.25, H), (0.49, H), (0.50, S), (1.00, S), (1.01, N)],
)
def test_rain_bands(in_hr, expected):
    assert rain_risk(in_hr) == expected


@pytest.mark.parametrize(
    "in_hr,expected",
    [(0, L), (0.49, L), (0.5, M), (0.99, M), (1.0, H), (1.99, H), (2.0, S), (3.0, S), (3.01, N)],
)
def test_snow_bands(in_hr, expected):
    assert snow_risk(in_hr) == expected


@pytest.mark.parametrize(
    "mph,weight,expected",
    [
        # >=55 is No Travel for any load
        (55, 0, N),
        # 45–54 + >30,000 lb -> No Travel; exactly 30,000 stays Severe
        (45, 30_001, N),
        (54.9, 80_000, N),
        (45, 30_000, S),
        # 35–44 + >40,000 lb -> Severe; exactly 40,000 stays High
        (35, 40_001, S),
        (44.9, 80_000, S),
        (35, 40_000, H),
        # load rules don't touch other wind bands
        (34.9, 80_000, M),
        (10, 80_000, L),
    ],
)
def test_wind_load_rules(mph, weight, expected):
    assert wind_risk(mph, weight) == expected


def test_overall_is_worst_condition():
    a = assess(wind_mph=30, rain_in_hr=0.3, snow_in_hr=0, weight_lb=LIGHT)
    assert (a.wind, a.rain, a.snow, a.overall) == (M, H, L, H)


def test_overall_includes_load_escalation():
    assert assess(wind_mph=40, rain_in_hr=0, snow_in_hr=0, weight_lb=45_000).overall == S
