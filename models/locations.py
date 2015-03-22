"""Data about filmed locations for a city. Primarily data from CSV dump + Google GeoCode API"""
from apis import tmdb
from geo.geomodel import GeoModel

from google.appengine.ext import db


class BaseLocation(GeoModel):
    """Base class for GeoCode API response driven location models"""

    # Place ID retrieved from GeoCode API is the key_name for this kind

    place_types = db.StringListProperty()  # Google Places types of location - just in case
    place_dump = db.TextProperty()  # Dump of GeoCode API response

    formatted_name = db.StringProperty(indexed=True)  # Formatted address* retrieved from GeoCode
    lower_formatted_name = db.StringProperty(indexed=True)


class City(BaseLocation):
    """Contains the formatted city name retrieved from GeoCode API as key_name and location geo point"""
    shorthand = db.StringProperty()  # Places API defined shorthand - SF for San Francisco, CA etc.

    def as_dict(self):
        return {
            'identifier': self.key().name(),
            'shorthand': self.shorthand,
            'formatted_name': self.formatted_name,
            'lat': self.location.lat,
            'lng': self.location.lon
        }


class Location(BaseLocation):
    """Location model for filmed locations. Contain the movie reference and basic data."""
    city = db.StringProperty(indexed=True)  # Place ID of the city
    city_formatted_name = db.StringProperty()  # Formatted name retrieved from GeoCode API
    city_location = db.GeoPtProperty()

    movie_id = db.StringProperty(indexed=True)
    movie_title = db.StringProperty()
    movie_release_date = db.StringProperty()
    movie_poster_path = db.StringProperty()

    def as_dict(self):
        return {
            'identifier': self.key().name(),
            'city': self.city,
            'city_name': self.city_formatted_name,
            'movie_id': self.movie_id,
            'movie_title': self.movie_title,
            'movie_release_date': self.movie_release_date,
            'movie_poster': tmdb.RESOURCE_URL.format(file_name=self.movie_poster_path),
            'lat': self.location.lat,
            'lng': self.location.lon,
            'formatted_name': self.formatted_name,
            'short_name': self.formatted_name.split(',', 1)[0]
        }
