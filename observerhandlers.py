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


class FrameHelper(object):
    """
    Since we cannot directly yield results inside a while loop, we simply wrap
    them in a helper object. `get_frame` will be called as the loop condition,
    and the frame will be accessible via `self.next_frame` if there is an
    available frame.
    """
    def __init__(self, frame_cache):
        self.frame_cache = frame_cache

        self.next_frame = None
        self.last_frame_time = time.time()

    def get_frame(self):
        """
        Gets the latest frame from the given cache. This must be run in a 
        ThreadPoolExecutor instance, enabling async operation. The executor 
        will handle setting the attributes of a Future object with either what
        we return or an exception if one is raised.

        :return True if we were able to get a frame, False if no more frames
                are available (i.e. stream is over)
        """


        self.next_frame = self.frame_cache.get_frame(self.last_frame_time)

        self.last_frame_time = time.time()

        return True

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

        # FrameHelper takes a frame cache... 
        # TODO: Implement getting the appropriate frame cache based on the slug.
        f_helper = FrameHelper(None)

        while (yield self.application.thread_pool.submit(f_helper.get_frame)):
            # The yield statement in the while loop will execute the future
            # returned by the thread_pool. The Future will return the result of
            # `FrameHelper.get_frame`. If True, there is a frame available,
            # which we can read out.
            frame = f_helper.next_frame

            self.write(b"--frame\r\n"
                       b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")

            # Flush the frame out
            self.flush()
