import json

from google.appengine.api import memcache

import base
from geo import geomath, geotypes
from models.locations import City, Location
from models.movies import Movie, Person

# Namespaced cache keys
MOVIE_KEY = 'Movie:{movie}:{city}'
SEARCH_KEY = 'Search:{city}:{query}'

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


def populate_bounds_and_locations(movie, city_id):
    """Adds bbox and locations keys with appropriate values to the given movie dict
    Returns True if successful, False if could not calculate the bounding box for some reason"""
    # Calculate bounding box of all locations
    ne = {'lat': -float('inf'), 'lng': -float('inf')}
    sw = {'lat': float('inf'), 'lng': float('inf')}
    locs = movie['city_locations'].get(city_id, [])
    for location in locs:
        ne['lat'] = max(ne['lat'], location['lat'])
        ne['lng'] = max(ne['lng'], location['lng'])
        sw['lat'] = min(sw['lat'], location['lat'])
        sw['lng'] = min(sw['lng'], location['lng'])
    if float('inf') in ne.values() or -float('inf') in sw.values():
        return False
    movie['bbox'] = {'sw': sw, 'ne': ne}
    movie['locations'] = locs
    movie.pop('city_locations', None)
    return True


@router('/json/movie/(.+)')
class MovieDetails(base.BaseHandler):
    """Returns all of the movie info to be shown on the client"""

    def _get(self, movie_id, *args, **kwargs):
        city_id = self.request.get('city')
        if not city_id:
            return self.send_error(400, "City is mandatory")

        cache_key = MOVIE_KEY.format(movie=movie_id, city=city_id)
        cache = memcache.get(cache_key)
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

        populate_bounds_and_locations(details, city_id)

        memcache.set(cache_key, json.dumps(details), 24*60*60)  # Cache for 24 hours

        self.send(details)


@router('/json/search')
class Autocomplete(base.BaseHandler):
    """Returns the possible auto completion suggestions"""

    def _get(self, *args, **kwargs):
        query = self.request.get('q').lower()
        city_id = self.request.get('city')
        if not query or not city_id:
            return self.send({
                'locations': [],
                'movies': []
            })

        cache_key = SEARCH_KEY.format(city=city_id, query=query)
        cache = memcache.get(cache_key)
        if cache:
            return self.send(json.loads(cache))

        # Get location suggestions
        locations = Location.all().filter(
            'city =', city_id
        ).filter(
            'lower_formatted_name >=', query
        ).filter(
            'lower_formatted_name <', query + u'\ufffd'
        ).order('lower_formatted_name').fetch(5)

        # Get movie suggestions
        movies = Movie.all().filter(
            'cities =', city_id
        ).filter(
            'lower_title >=', query
        ).filter(
            'lower_title <', query + u'\ufffd'
        ).order('lower_title').fetch(5)

        movies = [m.as_dict() for m in movies]

        broken_movies = []
        for i, movie in enumerate(movies):
            if not populate_bounds_and_locations(movie, city_id):
                broken_movies.append(i)

        for idx in broken_movies:
            del movies[idx]

        ret = {
            'locations': [l.as_dict() for l in locations],
            'movies': movies
        }
        memcache.set(cache_key, json.dumps(ret), 24*60*60)

        return self.send(ret)


@router('/json/cities')
class CityList(base.BaseHandler):
    """Sends back the list of cities in the system"""

    def _get(self, *args, **kwargs):
        all_cities = City.all().fetch(None)  # Assumption - we're going to have only a few cities
        return self.send(sorted([c.as_dict() for c in all_cities], key=lambda c: c['shorthand'] != 'SF'))
