import math

EARTH_RADIUS = 3959.9

def change_in_latitude(miles):
    """
    Given a distance north, return the change in latitude.
    """
    return math.degrees(miles/EARTH_RADIUS)
def change_in_longitude(latitude, miles):
    """
    Given a latitude and a distance west, return the change in longitude.
    Find the radius of a circle around the earth at given latitude.
    """
    r = EARTH_RADIUS*math.cos(math.radians(latitude))
    return math.degrees(miles/r)
