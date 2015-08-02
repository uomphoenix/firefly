"""
observerhandlers.py

Implements handler classes for the observer application. This provides an MVC
approach to serving web-based requests.
"""

import logging
import time

import tornado.web
import tornado.concurrent
from tornado import gen

def get_frame(frame_cache, last_frame_time):
    """
    Gets the latest frame from the given cache, and returns it using a future,
    enabling async operation.
    """

    future = tornado.concurrent.Future()

    future.set_result(frame_cache.get_frame(last_frame_time))

    return future

class BaseHandler(tornado.web.RequestHandler):
    def __init__(self, application, request, **kwargs):
        super(BaseHandler, self).__init__(application, request, **kwargs)

class RootHandler(BaseHandler):
    def get(self):
        self.write("list of streams:")

        # print a list of streams in some templated page

class StreamHandler(BaseHandler):
    @gen.coroutine
    def get(self, slug):
        last_frame_time = time.time()

        self.set_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")

        while True:
            # Get the appropriate feed cache based on the given slug
            frame_cache = None

            # Infinitely yield frames in a Future until the end of the stream!
            # This is where the magic is - tornado will yield execution of 
            # this handler to other handlers at this point, returning when
            # the future is done. This enables us to serve many clients
            # asynchronously. Note that we need to maintain a frame rate
            # as well.
            frame = yield get_frame(frame_cache, last_frame_time)

            if frame is None:
                # No frame found, end of stream
                break

            self.write(b"--frame\r\n"
                       b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")

            # Flush the frame out
            self.flush()

            # Set when we last sent a frame, so we can synchronize the frames
            last_frame_time = time.time()
