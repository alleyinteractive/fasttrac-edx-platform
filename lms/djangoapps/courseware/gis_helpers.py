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

# Great-circle method
def coordinates_distance(first, second):
    '''
    Measures distance between two geographical coordinates.
    Params
    - first: coordinate(latitude, longitude)
    - second: coordinate(latitude, longitude)

    Returns distance in miles
    '''
    latitude_1, longitude_1 = math.radians(
        float(first['latitude'])), math.radians(float(first['longitude']))
    latitude_2, longitude_2 = math.radians(
        float(second['latitude'])), math.radians(float(second['longitude']))

    sin_latitude_1, cos_latitude_1 = math.sin(latitude_1), math.cos(latitude_1)
    sin_latitude_2, cos_latitude_2 = math.sin(latitude_2), math.cos(latitude_2)

    delta_longitude = longitude_2 - longitude_1
    cos_delta_longitude, sin_delta_longitude = math.cos(
        delta_longitude), math.sin(delta_longitude)

    distance = math.atan2(math.sqrt((cos_latitude_2 * sin_delta_longitude) ** 2 +
                             (cos_latitude_1 * sin_latitude_2 -
                              sin_latitude_1 * cos_latitude_2 * cos_delta_longitude) ** 2),
                   sin_latitude_1 * sin_latitude_2 + cos_latitude_1 * cos_latitude_2 * cos_delta_longitude)

    return EARTH_RADIUS * distance
