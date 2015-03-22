import json

from google.appengine.api import memcache

import base
from geo import geomath, geotypes
from models.locations import City, Location
from models.movies import Movie, Person

# Namespaced cache keys
MOVIE_KEY = 'Movie:{}'
SEARCH_KEY = 'Search:{}'

router = base.Router()


@router('/')
class MapHandler(base.BaseHandler):

    def _get(self, *args, **kwargs):
        return self.render('index.html')


@router('/json/locations')
class BoundedLocations(base.BaseHandler):

    def _get(self, *args, **kwargs):
        bounds = self.request.get('bounds')
        center = self.request.get('center')
        try:
            bparts = map(float, bounds.split(','))
            cparts = map(float, center.split(','))
        except ValueError:
            return self.send_error(400, "Invalid bounds/center")

        if len(bparts) != 4 or len(cparts) != 2:
            return self.send_error(400, "Invalid bounds/center")

        bounding_box = geotypes.Box(*bparts)
        bounded = Location.bounding_box_fetch(Location.all(), bounding_box)

        center_pt = geotypes.Point(*cparts)
        bounded = sorted(bounded, key=lambda b: geomath.distance(center_pt, b.location))

        data = map(lambda b: b.as_dict(), bounded)
        for i, location in enumerate(data):
            location['idx'] = i

        return self.send(data)


# TODO: Add city specific map centering, at least initially
@router('/json/movie/(.+)')
class MovieDetails(base.BaseHandler):
    """Returns all of the movie info to be shown on the client"""

    def _get(self, movie_id, *args, **kwargs):
        cache = memcache.get(MOVIE_KEY.format(movie_id))
        if cache:
            return self.send(json.loads(cache))
        movie = Movie.get_by_key_name(movie_id)
        if movie is None:
            return self.send_error(400, 'Invalid movie id')

        details = movie.as_dict()
        persons = Person.get_by_key_name(details['cast'] + [details['director']] + details['writers'])

        num_cast = len(details['cast'])
        details['cast'] = map(lambda p: p.as_dict(), persons[:num_cast])
        details['director'] = persons[num_cast].as_dict()
        details['writers'] = map(lambda p: p.as_dict(), persons[num_cast+1:])

        memcache.set(MOVIE_KEY.format(movie_id), json.dumps(details), 24*60*60)  # Cache for 24 hours

        self.send(details)


@router('/json/search')
class Autocomplete(base.BaseHandler):
    """Returns the possible auto completion suggestions"""

    def _get(self, *args, **kwargs):
        query = self.request.get('q').lower()
        if not query:
            return self.send({
                'locations': [],
                'movies': []
            })

        cache = memcache.get(SEARCH_KEY.format(query))
        if cache:
            return self.send(json.loads(cache))

        # Get location suggestions
        locations = Location.all().filter(
            'lower_formatted_name >=', query
        ).filter(
            'lower_formatted_name <', query + u'\ufffd'
        ).order('lower_formatted_name').fetch(5)

        # Get movie suggestions
        movies = Movie.all().filter(
            'lower_title >=', query
        ).filter(
            'lower_title <', query + u'\ufffd'
        ).order('lower_title').fetch(5)

        ret = {
            'locations': [l.as_dict() for l in locations],
            'movies': [m.as_dict() for m in movies]
        }
        memcache.set(SEARCH_KEY.format(query), json.dumps(ret), 24*60*60)

        return self.send(ret)


@router('/json/cities')
class CityList(base.BaseHandler):
    """Sends back the list of cities in the system"""

    def _get(self, *args, **kwargs):
        all_cities = City.all().fetch(None)  # Assumption - we're going to have only a few cities
        return self.send(sorted([c.as_dict() for c in all_cities], key=lambda c: c['shorthand'] != 'SF'))
