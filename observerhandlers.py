"""
observerhandlers.py

Implements handler classes for the observer application. This provides an MVC
approach to serving web-based requests.
"""

import logging

import tornado.web

class BaseHandler(tornado.web.RequestHandler):
    def __init__(self, application, request, **kwargs):
        super(BaseHandler, self).__init__(application, request, **kwargs)

class RootHandler(BaseHandler):
    pass
