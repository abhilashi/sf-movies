import json
import logging
import re

import webapp2 as webapp
from google.appengine.api import taskqueue
from google.appengine.ext import db

from apis import google_, imdb, tmdb
from base import Router
from models import locations, movies

ADDRESS_RE = re.compile(r'(?P<address1>.*)(\((?P<address2>.*)\))')

router = Router('/task')


@router('/movie')
class MovieTask(webapp.RequestHandler):
    """Gets a movie's IMDB id and TMDB details and spawns tasks for creating locations for that movie"""

    def post(self):
        title = self.request.get('title')
        release_year = self.request.get('release_year')
        loc = json.loads(self.request.get('loc'))

        imdb_id = imdb.get_movie_id(title, release_year)

        if not imdb_id:
            logging.error('Fix movie details for: %s' % title)
            return

        details = tmdb.movie_details(imdb_id)
        if details is None:
            logging.error('Could not find any details for %s in TMDB' % title)
            return
        crew = tmdb.movie_credits(imdb_id)

        language = 'English'
        original_language = details.get('original_language')
        spoken_languages = details.get('spoken_languages', [])
        for lang in spoken_languages:
            values = lang.values()
            if original_language in values:
                language = lang['name']

        cast_ids = [str(c['id']) for c in (crew.get('cast') or [])]
        director_id = (crew.get('director') or {}).get('id')
        director_id = str(director_id) if director_id else None
        writer_ids = [str(w['id']) for w in (crew.get('writers') or [])]

        movie = movies.Movie(
            key_name=imdb_id,
            title=details.get('title') or title,
            lower_title=title.lower(),
            overview=details.get('overview'),
            poster_path=details.get('poster_path'),
            release_date=details.get('release_date'),
            language=language,
            tagline=details.get('tagline'),
            cast=cast_ids,
            director=director_id,
            writers=writer_ids,
            tmdb_dump=json.dumps({
                'details': details,
                'crew': crew
            })
        )
        movie.put()

        # Kick off tasks to populate Persons based on cast
        for person_id in filter(None, cast_ids + [director_id] + writer_ids):
            taskqueue.add(url='/task/person', params={
                'person_id': person_id
            })

        # Kick off location tasks
        city_formatted_name = self.request.get('city_formatted_name')
        city_location = self.request.get('city_location')
        city = self.request.get('city')
        for location in loc:
            taskqueue.add(url='/task/location', params={
                'movie_id': movie.key().name(),
                'movie_title': movie.title,
                'movie_release_date': movie.release_date,
                'movie_poster_path': movie.poster_path,
                'city': city,
                'city_location': city_location,
                'city_formatted_name': city_formatted_name,
                'data': json.dumps(location)
            })


@router('/location')
class LocationTask(webapp.RequestHandler):
    """Fetches and populates location data for each filming location using GeoCode API"""

    def post(self):
        city_formatted_name = self.request.get('city_formatted_name')  # The formatted name
        city = self.request.get('city')  # The place id
        city_location = json.loads(self.request.get('city_location'))
        city_location = db.GeoPt(city_location['lat'], city_location['lng'])

        data = json.loads(self.request.get('data'))
        addresses = [data['Locations']]
        match = ADDRESS_RE.match(data['Locations'])
        if match:
            addresses.extend([match.group('address1'), match.group('address2')])

        response = None
        for address in addresses:
            response = google_.get_location(city_formatted_name, address)
            if response is not None and response['place_id'] != city:
                break

        if response is None:
            # We're not going to add what we don't know
            logging.error('Location info could not be retrieved for: %s\n city: %s' % (data, city_formatted_name))
            return

        location_dict = response['geometry']['location']
        place_id = response['place_id']
        location = db.GeoPt(location_dict['lat'], location_dict['lng'])
        formatted_name = response.get('formatted_name') or '%s, %s' % (data['Locations'], city_formatted_name)

        loc = locations.Location(
            key_name=place_id,
            location=location,
            city=city,
            city_formatted_name=city_formatted_name,
            city_location=city_location,
            formatted_name=formatted_name,
            lower_formatted_name=formatted_name.lower(),
            place_types=response.get('place_types', []),
            place_dump=json.dumps(response),
            movie_id=self.request.get('movie_id'),
            movie_title=self.request.get('movie_title'),
            movie_release_date=self.request.get('movie_release_date'),
            movie_poster_path=self.request.get('movie_poster_path')
        )
        loc.update_location()
        loc.put()


@router('/person')
class PersonTask(webapp.RequestHandler):
    """Fetches and populates person data by id"""

    def post(self):
        person_id = self.request.get('person_id')
        name, imdb_id, profile_path = tmdb.person_details(person_id)
        person = movies.Person(key_name=str(person_id), name=name, imdb_id=imdb_id, profile_path=profile_path)
        person.put()
