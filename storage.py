"""
storage.py

This module provides classes and methods for writing videos to disk, as well as
a database interface for state persistence.

We use OpenCV to write the video, rather than directly subprocessing ffmpeg.
This makes it a bit more platform independent.
"""

import logging
import os
import time

import cv2
import numpy as np

import settings

class FFVideoWriter(object):
    """
    Wraps the video writing
    """
    def __init__(self, filename, fps, dim = (640,480), colour = True, 
                 codec = cv2.cv.CV_FOURCC('P','I','M','1')):
        

        self.filename = os.path.join(settings.storage.dir, filename)
        self._writer = cv2.VideoWriter(self.filename, codec, fps, dim, colour)

        logging.debug("Attempted to open video file %s. Opened: %d",
            self.filename, self._writer.isOpened())

    def write(self, frame):
        try:
            self._writer.write(np.fromstring(frame, dtype = np.uint8))

        except:
            logging.exception("Exception writing frame to disk, file: %s", 
                self.filename)

    def end(self):
        try:
            #self._writer.release()
            pass

        except:
            logging.exception("Exception releasing video file")

        del self._writer

    def __del__(self):
        cv2.cv.cvReleaseVideoWriter(self._writer)

class VideoStorageManager(object):
    """
    Manages writers for all existing streams (clients)
    """
    def __init__(self, feed_cache):
        self.feed_cache = feed_cache

        # Map of client -> last frame id
        self._flush_counter = {}
        # Map of client -> FFVideoWriter
        self._writers = {}

    def run(self):
        """
        Flush the cache every second
        """
        while True:

            self.flush_caches()

            time.sleep(1)

    def add_client(self, client):
        """
        Adds a client to be maintained by the manager
        """
        if (client not in self._flush_counter 
                and client not in self._writers):

            self._flush_counter[client] = -1

            video_name = client.identifier + time.strftime("_%Y-%m-%d-%H-%M") + '.avi'
            self._writers[client] = FFVideoWriter(video_name, 24)


    def flush_caches(self):
        """
        Flushes all new frames in existing caches to disk. We need to maintain
        a count of what frame was last flushed, much like the observer
        maintains a count so clients receive the latest frame...
        """
        logging.debug("Flushing caches")
        # We use the cache's lock to prevent concurrency issues with other
        # threads needing the same data while we're iterating...
        for client, writer in self._writers.iteritems():
            logging.debug("Checking client %s. Last fid: %d, cache: %s",
                client, self._flush_counter[client], client.cache)

            # Skip clients that don't have a frame cache yet
            if client.cache is None:
                continue

            frame, ts, fid = client.cache.get_frame(self._flush_counter[client])

            self._flush_counter[client] = fid

            writer.write(frame)
