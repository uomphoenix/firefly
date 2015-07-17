"""
receiver.py

This module handles video feed receiving. Requires communication with the
authentication server for challenge token verification. The video feed is
sent via UDP, so we can tolerate frame loss or temporary loss of connection.

The receiver maintains a cache of frames so clients that wish to view the
stream will receive at least some frames if none have been received for
some time.
"""

import logging
import SocketServer

from settings import receiver as recv_settings

import caching

class ReceiverHandler(SocketServer.BaseRequestHandler):
    """
    A new handler instance is created for every frame sent by whatever our
    transmitter is. Each handler is run in its own thread. We need to
    authenticate the request and if valid, store the frame under the
    client's unique ID. We can technically have multiple sources (i.e.
    a MIMO system).
    """
    def __init__(self, request, client_address, server):
        SocketServer.BaseRequestHandler.__init__(self, request, 
            client_address, server)

    def setup(self):
        pass

    def handle(self):
        """
        Handles the UDP packet. Data is sent in the format:
        challenge\0frame\0, where \0 is a null byte (0) acting as the delimiter
        """
        try:
            data = self.request[0][:-1] # Strip trailing null byte

            logging.debug("Received %s from %s", repr(data), self.client_address)
            delimited = data.split("\0")

            if len(delimited) != 2:
                logging.warn("Invalid fragment received from %s", 
                    self.client_address)

                return

            challenge_token, frame = delimited

            # Need to verify the challenge token and store the frame under the
            # token's UID
            uid = self.server.authenticate(challenge_token)

            if uid is None:
                logging.warn("Invalid challenge token given by %s", 
                    self.client_address)

            else:
                # store the frame in the cache
                self.server.cache_frame(uid, frame)

        except:
            logging.exception("An error occurred handling fragment from %s",
                self.client_address)

    def finish(self):
        pass


class ReceiverServer(SocketServer.ThreadingMixIn, SocketServer.UDPServer):
    def __init__(self, server_address, authenticator, 
                 handler = ReceiverHandler):
        """
        Set up cache and others, run super init.
        """
        SocketServer.UDPServer.__init__(self, server_address, handler)

        self.authenticator = authenticator

        self._caches = {}


        # Allow binding to the same address if the app didn't exit cleanly
        self.allow_reuse_address = True
        # Ensure request threads are terminated when the application exits
        self.daemon_threads = True

    def authenticate(self, token):
        """
        Encapsulates authentication.

        :param token The token to verify

        :return The UID the token belongs to, or None if the toke cannot be
                verified
        """
        uid = None

        try:
            uid = self.authenticator.authenticate_token(token)

        except:
            logging.exception("Error authenticating token '%s'", token)

        finally:
            return uid

    def cache_frame(self, uid, frame):
        """
        Add the frame to the appropriate cache. The cache object will handle
        the actual caching and maintaining the cache size, etc.

        :param uid The UID of the transmitter who sent the frame
        :param frame The raw frame data
        """
        cache = None
        if uid not in self._caches:
            cache = caching.FrameCache(recv_settings.cache_size)
            self._caches[uid] = cache

        else:
            cache = self._caches[uid]

        cache.add_frame(frame)

    def stop_server(self):
        """
        Stop listening and close the socket
        """
        self.shutdown()
        self.server_close()
