import math

EARTH_RADIUS_M = 6_371_008.8
METERS_PER_MILE = 1609.344


def haversine_m(a, b) -> float:
    """Great-circle distance in meters between two [lon, lat] points."""
    lon1, lat1, lon2, lat2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(h))
