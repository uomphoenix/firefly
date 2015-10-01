"""
cache.py

Provides methods and classes for maintaning and managing a video frame cache.
This module and its classes are thread-safe, as they are shared between
multiple application threads.
"""

import logging
import collections
import time
import threading
import operator

class NoCacheFoundError(Exception):
    """ Raised when no cache is found during a search """
    pass

class IncompleteFrameError(object):
    """ Raised when trying to get a frame from fragments when insufficient
    fragments exist """
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

    def cache_frame(self, client, sequence_num, max_fragments, fragment_num, 
                    frame):
        """
        Add the frame to the appropriate cache. The cache object will handle
        the actual caching and maintaining the cache size, etc.

        :param client The client object related to the transmitter that sent
                      the frame
        :param sequence_num The ID of the frame
        :param max_fragments The number of fragments in the sequence
        :param fragment_num The ID of the fragment in the sequence
        :param frame The raw frame data, potentially a fragment
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

        cache.add_frame(sequence_num, max_fragments, fragment_num, frame)

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

INITIAL_FRAMERATE = 30

class FrameCache(object):
    """
    The cache will be accessed from multiple threads, therefore we need to
    make it thread safe.
    """
    def __init__(self, size, client):
        self.client = client

        self.size = size
        self._cache = collections.deque(maxlen = size)

        # The fragment cache holds fragments until there's a complete frame to
        # build
        self._fragment_cache = {}

        self.lock = threading.RLock()

        self._last_framerate_guess = INITIAL_FRAMERATE

    def add_frame(self, sequence_num, max_fragments, fragment_num, fragment):
        """
        Adds a frame to this frame cache (or a fragment)

        :param sequence_num A number identifying the fragment's sequence
        :param max_fragments The number of fragments in the sequence
        :param fragment_num The number of this fragment
        :param fragment The frame fragment
        """
        with self.lock:
            # Try to get the fragment matching the frame...
            fragment_cache = None
            if sequence_num not in self._fragment_cache:
                fragment_cache = FragmentCache(sequence_num, max_fragments)

                self._fragment_cache[sequence_num] = fragment_cache
            else:
                fragment_cache = self._fragment_cache[sequence_num]

            fragment_cache.add_fragment(fragment_num, fragment)

            """logging.debug("Added fragment to fragment cache. seqnum: %d,"
                         " fragn: %d, maxfragn: %d", 
                         sequence_num, fragment_num, max_fragments)

            logging.debug("FragmentCache complete: %s, frag cache len: %d", 
                fragment_cache.is_fragment_complete(), len(fragment_cache))"""

            frame = None
            if fragment_cache.is_fragment_complete():
                frame = fragment_cache.get_complete_fragment()
            else:
                return


            if frame[-1] != "\xd9":
                logging.warn("Frame does not end in \\xd9")
                #logging.debug(repr(frame))

            ctime = time.time()
            to_cache = (frame, ctime, sequence_num)

            #logging.debug("Adding %s to cache", to_cache)

            # The deque will automatially remove items from the left side of
            # the cache since we specified a maxlen (if we were appending to
            # the left side, it'd remove from the right side)
            self._cache.append(to_cache)

            self.client.last_frame_update = time.time()

            self.get_framerate()

    def get_frame(self, last_fid):
        """
        Gets the most recent frame after the specified cutoff. We don't just
        get the most recent frame from the cache as that may not be the frame
        that the client requires. Therefore we use the timestamp.
        """

        #logging.debug("Attempting to get latest frame with ID cutoff %d", 
        #    last_fid)

        with self.lock:
            to_send = None

            for f, ts, fid in self._cache:
                if fid > last_fid:
                    # Get the frame with an ID > than the last one sent
                    logging.debug("selected a frame")
                    
                    to_send = (f, ts, fid)

                    break

            return to_send

    def is_stream_timed_out(self):
        """
        A stream is considered timed out if there has been more than 60 seconds
        since the last frame was received
        """
        return time.time() - self.client.last_frame_update > 10
        #return False

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

        time_diff = self._cache[-1][1] - self._cache[0][1]

        guess = cache_len / (time_diff if time_diff > 0 else 1)

        new_guess = (self._last_framerate_guess + guess)/2

        """logging.debug(
                "New framerate guess - ID: '%s', new: %d, old: %d",
                    self.client.identifier, new_guess, 
                    self._last_framerate_guess
            )"""

        self._last_framerate_guess = new_guess

        return new_guess

    def __len__(self):
        with self.lock:
            return len(self._cache)

class FragmentCache(object):
    def __init__(self, sequence_num, max_fragments):

        self.sequence_num = sequence_num

        self.max_fragments = max_fragments

        self._cache = []

        self.lock = threading.RLock()

        self._complete_fragment = None

    def is_fragment_complete(self):
        with self.lock:
            return len(self._cache) == self.max_fragments

    def add_fragment(self, fragment_id, fragment):
        with self.lock:
            #logging.debug("Adding fragment %d to fragment cache for seq %d",
            #    fragment_id, self.sequence_num)

            self._cache.append((fragment_id, fragment))

    def get_complete_fragment(self):
        with self.lock:
            if not self.is_fragment_complete():
                raise IncompleteFrameError("Frame %s is not complete" % (
                    self.sequence_num))

            if self._complete_fragment is None:
                # Construct the frame from fragments
                # We need to sort by fragment ID first, as the fragments may
                # not necessarily come in order...
                self._cache.sort(key = operator.itemgetter(0))

                # Join all fragments
                frame = "".join(x[1] for x in self._cache)

                self._complete_fragment = frame


            return self._complete_fragment

    def __len__(self):
        with self.lock:
            return len(self._cache)
