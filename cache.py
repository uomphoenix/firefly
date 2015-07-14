"""
cache.py

Provides methods and classes for maintaning and managing a video frame cache.
"""

import logging
import collections
import time
import threading

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

            self._cache.add(to_cache)

            # If the length of the cache is bigger than the allowed size, pop
            # the first item
            if len(self) > self.size:
                self._cache.popleft()

    def __len__(self):
        return len(self.cache)
