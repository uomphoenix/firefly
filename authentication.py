"""
authentication.py

Video feed transmitters are required to authenticate before the feed is
acknowledged. This class handles that authentication and generates a
challenge token which must be included in each transmitted frame. Since
UDP source address can be spoofed, this is necessary to prevent malicious
users injecting undesired frames into our stream! All relays authenticate
the same as the main feed source. Note that this does not handle MITM attacks.

We perform authentication only by token, not by IP as the remote (mobile)
address may change intermittently depending on coverage, connection loss,
etc. It may also be easily spoofed (UDP packets).

Authentication (challenge) tokens must be recorded and have a time limit on
them. We don't want to force the transmitter to re-authenticate if no
connection can be established for a short period, but we also don't want the
token to last forever.

Provides the authentication server and a modularised client for use by relays
and the multicopter itself.
"""

import logging
import SocketServer
import socket

from settings import authentication as auth_settings

# Temporarily hardcode this
CLIENT_WHITELIST = ['1.1.1.1']

class Authenticator(object):
    def __init__(self):
        pass

    def create_token(self, host):
        """
        Attempts to create a token for the given host. If a token exists,
        the existing one will be returned.

        :param host The host address of an authenticating client

        :return A challenge token, new or existing
        """
        
        pass

    def verify_token(self, token):
        pass


class AuthenticationServerHandler(SocketServer.BaseRequestHandler):
    """
    Handles authentication attempts. Note that this is a TCP stream - the
    connection remains open until either end hangs up. The protocol is
    designed to be as light-weight as possible, requiring minimal
    bandwidth (i.e. byte optimized). 

    An authentication attempt is in the form:
    \x01\x00

    A response is in the form:
    \x01\x00<challenge_token>\x00

    No additional parameters are required, and the source address must be
    whitelisted. TCP source is not spoofable like UDP sources (but can
    be manipulated in other malicious ways such as MITM attacks).
    """
    def __init__(self, request, client_address):
        super(AuthenticationServerHandler, self).__init__(request, 
            client_address)

    def setup(self):
        pass

    def handle(self):
        """
        Handle the TCP request. As this is a stream and not a UDP packet, we
        cannot just get the entire packet at once. Thefore, we attempt to read
        from the buffer.
        """
        # Since we only expect small packets, we don't need to read a buffer of
        # size, say, 4096.
        data = self.request.recv(64)

        logging.debug("Received '%s' from '%s'", data, self.client_address[0])

        if data[0:2] == "\x01\x00":
            # Authentication attempt. Since this address is whitelisted (as it
            # was successfully verified by the server in `verify_request`), we
            # can safely acknowledge the authentication.

            self.request.send("\x01\x00%s\x00" % (
                    self.server.authenticator.create_token(
                            self.client_address[0]
                        ),
                    )
                )

        else:
            logging.info("Unknown request '%s' from '%s'", 
                data, self.client_address[0])

            self.request.send("")


    def finish(self):
        # Close the connection once we've finished handling it
        self.request.close()

class AuthenticationServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer):
    def __init__(self, server_address, authenticator, 
                 handler = AuthenticationServerHandler):

        super(AuthenticationServer, self).__init__(server_address, handler)

        self.authenticator = authenticator

        # Allow binding to the same address if the app didn't exit cleanly
        self.allow_reuse_address = True

    def verify_request(self, request, client_address):
        chost, cport = client_address

        allowed = chost in CLIENT_WHITELIST

        logging.debug("Verifying request from '%s'. Allowed: %s", 
            chost, allowed)

        return allowed

class AuthenticationClient(object):
    pass
