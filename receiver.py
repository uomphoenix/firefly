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

class Handler(SocketServer.BaseRequestHandler):
    """
    A new handler instance is created for every frame sent by whatever our
    transmitter is. Each handler is run in its own thread. We need to
    authenticate the request and if valid, store the frame under the
    client's unique ID. We can technically have multiple sources (i.e.
    a MIMO system).
    """
    def __init__(self, request, client_address, server):
        super(Handler, self).__init__(request, client_address, server)

    def setup(self):
        pass

    def handle(self):
        """
        Handles the UDP packet. Data is sent in the format:
        challenge\0frame\0, where \0 is a null byte (0) acting as the delimiter
        """
        try:
            data = self.request[0][:-1] # Strip trailing null byte
            delimited = data.split("\0")

            if len(delimited) != 2:
                logging.warn("Invalid fragment received from %s", 
                    self.client_address)

                return

            challenge_token, frame = delimited

            # Need to verify the challenge token and store the frame under the
            # token's UID
            uid = self.server.authenticate(challenge_token)

            if uid is not None:
                # store the frame in the cache
                pass

        except:
            logging.warn("An error occurred handling fragment from %s",
                self.client_address)

    def finish(self):
        pass


class Receiver(SocketServer.ThreadingMixIn, SocketServer.UDPServer):
    def __init__(self, server_address, handler, authenticator):
        """
        Set up cache and others, run super init.
        """

        self._authenticator = authenticator

        super(Receiver, self).__init__(server_address, handler)

    def authenticate(self, token):
        """
        Encapsulates authentication.

        :param token The token to verify

        :return The UID the token belongs to, or None if the toke cannot be
                verified
        """
        uid = None

        try:
            uid = self._authenticator.
        except:
            logging.exception("Error authenticating token '%s'", token)
        finally:
            return uid

    def stop_server(self):
        """
        Stop listening and close the socket
        """
        self.shutdown()
        self.server_close()
