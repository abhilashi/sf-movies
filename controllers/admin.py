"""Implements the admin functionality - namely, uploading a movie location in a city, individually or in bulk"""
import csv
import json
from collections import defaultdict

from google.appengine.api import taskqueue
from google.appengine.ext import db

import base
from apis import google_
from models import locations

router = base.Router('/admin')


@router('')
class AdminPage(base.BaseHandler):
    """Renders the admin console"""

    def _get(self, *args, **kwargs):
        """Renders the admin page"""
        self.render('admin.html')


@router('/upload')
class UploadMovieLocations(base.BaseHandler):
    """Takes in a csv file and a city and uploads multiple at once"""

    def _post(self, *args, **kwargs):
        city = self.request.get('city') or 'San Francisco, CA'
        response = google_.get_location(city, '')
        if response is None:
            return self.send_error(400, 'Invalid city')
        location_dict = response['geometry']['location']
        place_id = response['place_id']
        shorthand = response['address_components'][0]['short_name']

        location = db.GeoPt(location_dict['lat'], location_dict['lng'])
        formatted_name = response.get('formatted_address', city)
        city = locations.City(key_name=place_id, formatted_name=formatted_name, location=location, place_id=place_id,
                              place_dump=json.dumps(response), place_types=response.get('types', []),
                              shorthand=shorthand)
        city.update_location()
        city.put()

        dump = self.request.POST.get('csv')
        reader = csv.DictReader(dump.file)
        movie_map = defaultdict(list)
        for row in reader:
            if not row.get('Locations'):
                # Ignore the rows that do not have a location specified
                continue
            movie_map[(row['Title'], row['Release Year'])].append(row)

        # Kick off individual movie handling task
        for movie, rows in movie_map.iteritems():
            title, release_year = movie
            taskqueue.add(url='/task/movie', params={
                'title': title,
                'release_year': release_year,
                'city_formatted_name': formatted_name,
                'city_location': json.dumps(location_dict),
                'city': place_id,
                'loc': json.dumps(rows)
            })

        self.redirect('/admin')

    def required_params(self):
        return ['city', 'csv']
