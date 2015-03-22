"""Retrieves location data (lat, lon) from foursquare"""
import urllib
from collections import namedtuple

from google.appengine.api import urlfetch

FS_API_URL = 'https://api.foursquare.com/v2/venues/search'
FS_CLIENT_ID = 'Q3SM0TN5LJEQZIZUVWQXVMIKAD5AW13OPWWKGXVQGDBLPWZG'
FS_CLIENT_SECRET = '3B45VAD3KCDIFPRICE5RQL2KPATAYH0OJVSTUJ11SNNT5L11'

Location = namedtuple('Location', ['latitude', 'longitude'])


def location(place, city='San Francisco, CA'):
    """Returns a Location namedtuple with latitude and longitude. Returns None if not found."""
    params = urllib.urlencode({
        'near': city,
        'intent': 'match',
        'query': place,
        'client_id': FS_CLIENT_ID,
        'client_secret': FS_CLIENT_SECRET
    })
    response = urlfetch.fetch(url='{}?{}'.format(FS_API_URL, params), method=urlfetch.GET)
    if response.status_code != 200:
        return None
