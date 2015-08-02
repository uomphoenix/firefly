"""
observerhandlers.py

Implements handler classes for the observer application. This provides an MVC
approach to serving web-based requests.
"""

import logging
import time

import tornado.web
from tornado.web import HTTPError
import tornado.concurrent
from tornado import gen

class NoFrameFoundError(Exception):
    """ Raised when we cannot get the next frame for some reason """
    pass

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
        # Start at -1 so we can get the 0th frame
        self.last_frame_id = -1

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

        frame_info = None
        stream_finished = False

        while frame_info is None and not stream_finished:
            # Sleep the frame period (1/framerate)
            time.sleep(1/self.frame_cache.get_framerate())
            #time.sleep(1)

            stream_finished = self.frame_cache.is_stream_timed_out()

            frame_info = self.frame_cache.get_frame(self.last_frame_id)

            stream_finished = time.time() - self.last_frame_time > 10

        if stream_finished:
            return False

        else:
            self.next_frame, _, self.last_frame_id = frame_info

            logging.debug("Got next frame for cache %s. Frame ID: %d", 
                self.frame_cache, self.last_frame_id)

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
        # FrameHelper takes a frame cache... 
        try:
            frame_cache = self.application.feed_cache.get_cache(slug)

        except:
            logging.exception(
                    "Excepting getting frame cache matching identifier '%s'",
                        slug
                )

            raise HTTPError(400)

        f_helper = FrameHelper(frame_cache)

        self.set_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")

        while (yield self.application.thread_pool.submit(f_helper.get_frame)):
            # The yield statement in the while loop will execute the future
            # returned by the thread_pool. The Future will return the result of
            # `FrameHelper.get_frame`. If True, there is a frame available,
            # which we can read out.
            frame = f_helper.next_frame

            logging.debug("Sending frame %s to client", repr(frame))

            self.write(b"--frame\r\n"
                       b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")

            # Flush the frame out
            self.flush()
