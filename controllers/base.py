"""This is where the server side controllers go"""
import json
import logging
import os
import traceback

import webapp2 as webapp

TEMPLATE_DIR = 'templates'


class Router(object):
    """Handles routes as decortors"""

    def __init__(self, prefix=''):
        """Each router can have a prefix - enables all routes in a module be prefixed appropriately
        Including the leading '/' in the prefix is caller's responsibility"""
        self.routes = []
        self.prefix = prefix

    def __call__(self, path):
        """Whenever the route object gets called, a.k.a. the decorator"""
        def decorator(handler):
            self.routes.append(('%s%s' % (self.prefix, path), handler))
            handler.PATH = path
            return handler
        return decorator

    @property
    def list(self):
        """Returns the accumulated route list so far, call at the end of any module"""
        return self.routes

router = Router()


# Warm up handler to load all modules
@router('/_ah/warmup')
class WarmupHandler(webapp.RequestHandler):
    """Does nothing, loading this package to handle this itself is good enough"""
    def get(self):
        pass


# Application specific
def fetch_template(name, mode='r'):
    """Returns the template file object by name - name should be fully qualified path inside templates folder"""
    curr_dir = os.path.dirname(__file__)
    file_dir = os.path.normpath(os.path.join(curr_dir, '..', TEMPLATE_DIR))
    return open(os.path.join(file_dir, name), mode=mode)


class BaseHandler(webapp.RequestHandler):
    """Base class for pretty much all request handlers"""

    def _get(self, *args, **kwargs):
        raise NotImplementedError

    def _post(self, *args, **kwargs):
        raise NotImplementedError

    def get(self, *args, **kwargs):
        if self.validate():
            try:
                self._get(*args, **kwargs)
            except Exception:
                logging.error(traceback.format_exc())
                self.send_error(500, 'An error occurred')
        else:
            # Taken care of inside .validate
            pass

    def post(self, *args, **kwargs):
        if self.validate():
            try:
                self._post(*args, **kwargs)
            except Exception:
                logging.error(traceback.format_exc())
                self.send_error(500, 'An error occurred')
        else:
            # Taken care of inside .validate
            pass

    def send(self, res):
        """Method to send JSON data without having to bend over backwards each time"""
        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(json.dumps(res))

    def render(self, template):
        """Shorthand for writing a template"""
        self.response.headers['Content-Type'] = 'text/html'
        tfile = fetch_template(template)
        self.response.out.write(tfile.read())

    def send_error(self, code, message):
        """Send back error json, common method for consistency"""
        self.error(code)
        self.send({'error': message})

    def validate(self):
        """Returns whether or not the request is valid"""
        # Check if all required params are available
        for param in self.required_params():
            if not self.request.get(param):
                self.send_error(400, 'Missing params')
                return False
        return True

    def required_params(self):
        """Can be implemented by subclasses for validation.
        Returns list of required params other than secret and version."""
        return []
