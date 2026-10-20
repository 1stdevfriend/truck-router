"""Weather risk classification from the assessment's threshold and load rules.

Band edges in the spec overlap (e.g. rain "0.10–0.25" then "0.25–0.50");
each band's lower bound is inclusive, so 0.25 in/hr is High.
"""

from dataclasses import dataclass
from enum import IntEnum


class Risk(IntEnum):
    LOW = 0
    MODERATE = 1
    HIGH = 2
    SEVERE = 3
    NO_TRAVEL = 4


# (lower bound inclusive, level), checked from highest to lowest.
WIND_BANDS = ((55, Risk.NO_TRAVEL), (45, Risk.SEVERE), (35, Risk.HIGH), (25, Risk.MODERATE))
RAIN_BANDS = ((0.50, Risk.SEVERE), (0.25, Risk.HIGH), (0.10, Risk.MODERATE))
SNOW_BANDS = ((2.0, Risk.SEVERE), (1.0, Risk.HIGH), (0.5, Risk.MODERATE))
# Rain and snow are No Travel only strictly above the Severe band's top.
RAIN_NO_TRAVEL_ABOVE = 1.00
SNOW_NO_TRAVEL_ABOVE = 3.0


def _band(value: float, bands, no_travel_above: float | None = None) -> Risk:
    if no_travel_above is not None and value > no_travel_above:
        return Risk.NO_TRAVEL
    for lower, level in bands:
        if value >= lower:
            return level
    return Risk.LOW


def wind_risk(wind_mph: float, weight_lb: float) -> Risk:
    level = _band(wind_mph, WIND_BANDS)
    if level == Risk.SEVERE and weight_lb > 30_000:
        return Risk.NO_TRAVEL
    if level == Risk.HIGH and weight_lb > 40_000:
        return Risk.SEVERE
    return level


def rain_risk(rain_in_hr: float) -> Risk:
    return _band(rain_in_hr, RAIN_BANDS, RAIN_NO_TRAVEL_ABOVE)


def snow_risk(snow_in_hr: float) -> Risk:
    return _band(snow_in_hr, SNOW_BANDS, SNOW_NO_TRAVEL_ABOVE)


@dataclass(frozen=True)
class Assessment:
    wind: Risk
    rain: Risk
    snow: Risk

    @property
    def overall(self) -> Risk:
        return max(self.wind, self.rain, self.snow)


def assess(wind_mph: float, rain_in_hr: float, snow_in_hr: float, weight_lb: float) -> Assessment:
    return Assessment(
        wind=wind_risk(wind_mph, weight_lb),
        rain=rain_risk(rain_in_hr),
        snow=snow_risk(snow_in_hr),
    )
