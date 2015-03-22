"""Client for TheMovieDB.org api"""
import json
import logging
import urllib

from google.appengine.api import urlfetch

API_KEY = '4c4f857399534d0d27c61d07d0476a21'
API_BASE_URL = 'http://api.themoviedb.org/3'
RESOURCE_URL = 'http://image.tmdb.org/t/p/original{file_name}'

MOVIE_DETAILS_PATH = '/movie/{movie_id}'
CREDITS_PATH = '/movie/{movie_id}/credits'
PERSON_DETAILS_PATH = '/person/{person_id}'


def tmdb_response(path, error_msg=''):
    params = urllib.urlencode({'api_key': API_KEY})
    response = urlfetch.fetch(url='%s%s?%s' % (API_BASE_URL, path, params), method=urlfetch.GET)

    if not response.status_code == 200:
        logging.error(error_msg.format(code=response.status_code))
        return None

    return json.loads(response.content)


def movie_details(imdb_id):
    """Returns the details of the movie identified by the imdb id"""
    path = MOVIE_DETAILS_PATH.format(movie_id=imdb_id)
    error_msg = 'Request for movie with id: %s, errored out with code: {code}' % imdb_id
    return tmdb_response(path, error_msg)


def movie_credits(imdb_id):
    """Returns the credits of interest (top 4 cast, top 4 direction and top 4 writers)"""
    path = CREDITS_PATH.format(movie_id=imdb_id)
    error_msg = 'Request for movie credits with id: %s, errored out with code: {code}' % imdb_id
    response = tmdb_response(path, error_msg)

    if response is None:
        return None

    cast = []
    for actor in response.get('cast', []):
        cast.append(actor)
        if len(cast) == 4:
            break

    director = None
    writers = []
    for crew in response.get('crew', []):
        job = crew.get('job', '').lower()
        if job == 'director':
            director = crew

        if len(writers) < 4:
            department = crew.get('department', '').lower()
            if department == 'writing':
                writers.append(crew)

    return {
        'cast': cast,
        'director': director,
        'writers': writers
    }


def person_details(person_id):
    """Returns the name, imdb id and profile picture path of the person with the given TMDB id"""
    path = PERSON_DETAILS_PATH.format(person_id=person_id)
    error_msg = 'Request for person with id: %s, errored out with code: {code}' % person_id
    details = tmdb_response(path, error_msg)
    return details['name'], details.get('imdb_id'), details.get('profile_path')
