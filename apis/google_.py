"""Google geo code api client to retrieve city's longitude and latitude"""
import json
import logging
import urllib

from google.appengine.api import urlfetch

GEOCODE_API_URL = 'https://maps.googleapis.com/maps/api/geocode/json'
SERVER_API_KEY = 'AIzaSyCBAbIKqhL4OYc-xsVLTz7ft8lwzKgS_hQ'
BROWSER_API_KEY = 'AIzaSyA1r_ROLa-lH6WzTz_sMuzBVyOXFKShKw8'


# GeoCode API stuff
def get_location(city, place):
    """Returns the geo location, place id and api response for a given place.
    Returns the data for the city itself, if place is omitted"""
    # Escape city and place - urllib is dumb
    city = city.encode('ascii', 'ignore')
    place = place.encode('ascii', 'ignore')
    params = urllib.urlencode({
        'address': ('%s, %s' % (place, city)) if place else city,
        'key': SERVER_API_KEY
    })
    response = urlfetch.fetch(url='%s?%s' % (GEOCODE_API_URL, params), method=urlfetch.GET)
    if response.status_code != 200:
        logging.error('For City: %s, Place: %s, Error Code: %s' % (city, place, response.status_code))
        return None

    json_response = json.loads(response.content)
    if json_response.get('status') != 'OK':
        logging.error('For City: %s, Place: %s, Unexpected response: %s' % (city, place, response.content))
        return None

    results = json_response.get('results', None)
    if not results:
        logging.error('For City: %s, Place: %s, No results found')
        return None

    # Assumption: The first result is in fact what we want
    return results[0]
