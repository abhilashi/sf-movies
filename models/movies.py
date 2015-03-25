"""Models to store data pertaining to individual movies, retrieved through themoviedb.org and admin uploads"""
import json

from google.appengine.ext import db

from apis.tmdb import RESOURCE_URL


class Person(db.Model):
    """Represents an actor. TMDB id (<\d+>) will be the key_name"""
    name = db.StringProperty()
    imdb_id = db.StringProperty()
    profile_path = db.StringProperty()

    def as_dict(self):
        return {
            'name': self.name,
            'imdb_id': self.imdb_id,
            'profile_path': (RESOURCE_URL.format(file_name=self.profile_path) if self.profile_path
                             else '/static/img/default_actor.png')
        }


class Movie(db.Model):
    """Stores information to display on individual movie pages, key_name is imdb id (tt<\d+>)"""
    title = db.StringProperty(indexed=True)
    lower_title = db.StringProperty(indexed=True)
    release_date = db.StringProperty()
    poster_path = db.StringProperty()  # Eventually, may want to retrieve and store image locally
    language = db.StringProperty()
    tagline = db.TextProperty()
    overview = db.TextProperty()

    cast = db.StringListProperty()  # TMDB ids tied to people - max 4
    director = db.StringProperty()  # TMDB id tied to people
    writers = db.StringListProperty()  # TMDB ids tied to people - max 4

    cities = db.StringListProperty(default=[], indexed=True)  # The list of city ids associated with this movie
    city_locations = db.TextProperty(default='{}')  # JSON mapping city ids to array of location ids

    tmdb_dump = db.TextProperty()  # TMDB is definitely not for real time requests

    def as_dict(self):
        return {
            'identifier': self.key().name(),
            'title': self.title,
            'release_date': self.release_date,
            'poster_path': (RESOURCE_URL.format(file_name=self.poster_path) if self.poster_path
                            else '/static/img/default_movie.png'),
            'language': self.language,
            'tagline': self.tagline,
            'overview': self.overview,
            'cast': self.cast,
            'director': self.director,
            'writers': self.writers,
            'cities': sorted(self.cities),
            'city_locations': json.loads(self.city_locations)
        }
