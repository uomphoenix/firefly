"""
cache.py

Provides methods and classes for maintaning and managing a video frame cache.
"""

import logging
import collections
import time
import threading

class FeedCache(object):
    """
    The feed cache holds a FrameCache object for every feed being served
    by the daemon. This is necessary for us to share the cache between
    multiple providers (i.e. between the observer, relay and receiver
    servers).
    """
    def __init__(self, max_cache_size):
        self.max_cache_size = max_cache_size

        self.caches = {}

        self.lock = threading.RLock()

    def cache_frame(self, uuid, frame):
        """
        Add the frame to the appropriate cache. The cache object will handle
        the actual caching and maintaining the cache size, etc.

        :param uuid The UUID of the transmitter who sent the frame
        :param frame The raw frame data
        """
        cache = None

        # We need to lock this so multiple caches cannot be created/overriden
        # for the same UUID by multiple threads
        with self.lock:
            if uuid not in self.caches:
                cache = FrameCache(self.max_cache_size)
                self.caches[uuid] = cache

            else:
                cache = self.caches[uuid]

        cache.add_frame(frame)

class FrameCache(object):
    """
    The cache will be accessed from multiple threads, therefore we need to
    make it thread safe.
    """
    def __init__(self, size):
        self.size = size
        self._cache = collections.deque()

        self.lock = threading.RLock()

    def add_frame(self, frame):
        with self.lock:
            to_cache = (frame, time.time())

            self._cache.append(to_cache)

            # If the length of the cache is bigger than the allowed size, pop
            # the first item
            if len(self) > self.size:
                self._cache.popleft()

    def get_frame(self, time_cutoff):
        """
        Gets the most recent frame after the specified cutoff. We don't just
        get the most recent frame from the cache as that may not be the frame
        that the client requires. Therefore we use the timestamp.
        """
        with self.lock:
            to_send = None

            for f, ts in self._cache:
                if ts > time_cutoff:
                    # Reached first frame which has a more recent timestamp.
                    # This is the frame that we want to send
                    to_send = f
                    break

            return to_send

    def __len__(self):
        with self.lock:
            return len(self._cache)
