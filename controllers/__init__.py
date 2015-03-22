__author__ = 'prudhvi'

import admin
import base
import client
import tasks

routes = admin.router.list
routes += base.router.list
routes += client.router.list
routes += tasks.router.list
