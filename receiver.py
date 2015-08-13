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
        <challenge>\x00<seq num>\x00<max fragments>\x00<fragment num>\x00<frame>\x00,
        where \x00 is a character delimiting the fragment. <seq num> is a 
        unique number identifying the frame and <fragment num> is a number 
        identifying which part of the frame this fragment belongs to. 
        <max fragments> is a number indicating how many fragments are in the
        sequence.
        Note that the frame itself may have \x00 in its binary, therefore we
        should simply join everything after our control parameters.

        This protocol allows for 'split-packet' sending of frames, i.e. a frame
        can be split into multiple packets, allowing large frames to be sent
        despite the ~65kB limit of UDP packets.
        """
        try:
            data = self.request[0]

            #logging.debug("Received %s from %s", repr(data), self.client_address)
            delimited = data.split("\x00")

            print delimited

            if len(delimited) < 5:
                logging.warn("Invalid fragment received from %s", 
                    self.client_address)

                return

            challenge_token = delimited[0]
            sequence_num = delimited[1]
            max_fragments = delimited[2]
            fragment_num = delimited[3]
            
            frame = "".join(delimited[4:-1])

            # Need to verify the challenge token and store the frame under the
            # token's UID
            client = self.server.authenticate(challenge_token)

            if client is None:
                logging.warn("Invalid challenge token given by %s", 
                    self.client_address)

            else:
                # store the frame in the cache
                self.server.cache_frame(client, sequence_num, max_fragments, fragment_num, frame)

        except:
            logging.exception("An error occurred handling fragment from %s",
                self.client_address)

    def finish(self):
        pass


class ReceiverServer(SocketServer.ThreadingMixIn, SocketServer.UDPServer):
    def __init__(self, server_address, authenticator, feed_cache,
                 handler = ReceiverHandler):
        """
        Set up cache and others, run super init.
        """

        # Allow binding to the same address if the app didn't exit cleanly
        self.allow_reuse_address = True
        # Ensure request threads are terminated when the application exits
        self.daemon_threads = True

        SocketServer.UDPServer.__init__(self, server_address, handler)

        self.authenticator = authenticator
        self.feed_cache = feed_cache
        

    def authenticate(self, token):
        """
        Encapsulates authentication.

        :param token The token to verify

        :return The client the token belongs to, or None if the toke cannot be
                verified
        """
        client = None

        try:
            client = self.authenticator.authenticate_token(token)

        except:
            logging.exception("Error authenticating token '%s'", token)

        finally:
            return client

    def cache_frame(self, client, sequence_num, max_fragments, fragment_num, 
                    frame):
        """
        Add the frame to the appropriate cache. The cache object will handle
        the actual caching and maintaining the cache size, etc.

        :param client The client corresponding to the frame transmitter
        :param sequence_num The ID of the frame
        :param max_fragments The number of fragments in the sequence
        :param fragment_num The ID of the fragment in the sequence
        :param frame The raw frame data (posssibly split)
        """
        try:
            self.feed_cache.cache_frame(client, sequence_num, max_fragments, 
                                        fragment_num, frame)
            
        except:
            logging.exception("Exception caching frame for %s", client)

    def stop_server(self):
        """
        Stop listening and close the socket
        """
        self.shutdown()
        self.server_close()
