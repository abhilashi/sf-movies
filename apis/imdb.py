"""Client for IMDB api - Used to get the movie id, that is later used in TMDB requests"""
import json
import logging
import urllib
import urlparse
from functools import partial

from google.appengine.api import urlfetch

IMDB_SEARCH_URL = 'http://www.imdb.com/xml/find'
IMDB_MOVIE_PARAMS = {  # Default params to retrieve movie results. Pass in 'q'.
    'json': 1,
    'tt': 'on'
}
IMDB_ACTOR_PARAMS = {  # Default params to retrieve actor results. Pass in 'q'.
    'json': 1,
    'nm': 'on'
}


def most_probable_match(release_year, results):
    """Returns the best probable match for the given movie out of a result set"""
    for result in results:
        # Assumption: Only one of the movies with this title is released in a 3 year window
        try:
            year = int(result.get('title_description', '')[:4])
        except ValueError:
            # Description doesn't start with the release year, giving up
            return None
        if int(release_year) in xrange(year-1, year+2):
            # Forgiving release year for being a year off
            return result
    return None


# TODO: Explore TMDB search API for this?
def get_movie_id(title, release_year):
    """Given a movie name, returns the IMDB movie id"""
    movie_name = title
    params = urllib.urlencode(dict(q=movie_name, **IMDB_MOVIE_PARAMS))
    response = urlfetch.fetch(url='{}?{}'.format(IMDB_SEARCH_URL, params),
                              method=urlfetch.GET, follow_redirects=False)

    if response.status_code == 302:
        # IMDB redirects to the movie page if only one match is found
        path = urlparse.urlparse(response.headers['location']).path
        return filter(None, path.split('/'))[-1]

    if response.status_code != 200:
        logging.error('Error response: %s\n for Movie: %s, Year: %s' % (response, title, release_year))
        return None

    results = json.loads(response.content)

    matcher = partial(most_probable_match, release_year)
    # Fact: There can always be multiple movies with the exact same name
    match = None
    for kind in ['exact', 'popular', 'substring']:
        matches = results.get('title_%s' % kind, [])
        match = matcher(matches)
        if match:
            break
    else:
        logging.error('Release year: %s did not match for title: %s' % (release_year, title))

    return match['id'] if match else None
