"""
cache.py

Provides methods and classes for maintaning and managing a video frame cache.
"""

import logging
import collections
import time
import threading

class NoCacheFoundError(Exception):
    """ Raised when no cache is found during a search """
    pass

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

    def cache_frame(self, client, frame):
        """
        Add the frame to the appropriate cache. The cache object will handle
        the actual caching and maintaining the cache size, etc.

        :param client The client object related to the transmitter that sent
                      the frame
        :param frame The raw frame data
        """
        cache = None

        # We need to lock this so multiple caches cannot be created/overriden
        # for the same client by multiple threads
        with self.lock:
            if client not in self.caches:
                cache = FrameCache(self.max_cache_size, client)

                self.caches[client] = cache
                client.cache = cache

            else:
                cache = self.caches[client]

        cache.add_frame(frame)

    def get_cache(self, cache_id):
        """
        Tries to find a FrameCache matching the given cache_id.

        :param cache_id The ID of the FrameCache to search for

        :return A FrameCache object matching the given ID

        :raises NoCacheFoundError When no cache can be found matching the ID
        """

        with self.lock:
            for c in self.caches.values():
                if c.client.identifier == cache_id:
                    return c

        raise NoCacheFoundError("No cache found matching ID %s" % cache_id)

INITIAL_FRAMERATE = 15

class FrameCache(object):
    """
    The cache will be accessed from multiple threads, therefore we need to
    make it thread safe.
    """
    def __init__(self, size, client):
        self.client = client

        self.size = size
        self._cache = collections.deque(maxlen = size)

        self.lock = threading.RLock()

        self._last_framerate_guess = INITIAL_FRAMERATE

    def add_frame(self, frame):
        with self.lock:
            ctime = time.time()

            to_cache = (frame, ctime)

            # The deque will automatially remove items from the left side of
            # the cache since we specified a maxlen (if we were appending to
            # the left side, it'd remove from the right side)
            self._cache.append(to_cache)

            self.client.last_frame_update = ctime

            self.get_framerate()

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

    def is_stream_timed_out(self):
        """
        A stream is considered timed out if there has been more than 60 seconds
        since the last frame was received
        """
        return time.time() - self.client.last_frame_update > 60

    def get_framerate(self):
        """
        The framerate is approximately the number of frames in cache/time 
        between first and last frame received in the cache. We go a bit
        more in-depth and use a moving average every time this method is
        invoked.
        """
        cache_len = len(self)

        if cache_len == 0:
            return self._last_framerate_guess

        time_diff = self._cache[:-1][1] - self._cache[0][1]

        guess = cache_len / (time_diff if time_diff > 0 else 1)

        new_guess = (self._last_framerate_guess + guess)/2

        logging.debug(
                "New framerate guess - ID: '%s', new: %d, old: %d",
                    self.client.identifier, new_guess, 
                    self._last_framerate_guess
            )

        self._last_framerate_guess = new_guess

        return new_guess

    def __len__(self):
        with self.lock:
            return len(self._cache)
