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
import time
import uuid
import threading
import random
import string

from settings import authentication as auth_settings

# Temporarily hardcode this
CLIENT_WHITELIST = ['192.168.101.1']

def rand_token(length, chars = string.digits):
    """
    At the moment, the token is only digits. This is to conserve bandwidth. It
    should also be rather short (i.e. no more than 12 or so digits)
    """
    return "".join(random.SystemRandom().choice(chars) for _ in range(length))

class NoClientFoundError(Exception):
    """ Raised when we cannot find a client matching a given host/token """
    pass

class InvalidAuthenticationTokenError(Exception):
    """ Raised when unable to authenticate a token """
    pass

class AuthenticatedClient(object):
    """
    A simple data object which retains information for a client who has
    authenticated.
    """
    def __init__(self, host, token = None):
        self.host = host
        self.time_created = time.time()

        self.uuid = uuid.uuid4()
        
        if token is None:
            self.token = rand_token(8)
        else:
            self.token = token

        self.last_frame_update = self.time_created

class Authenticator(object):
    def __init__(self):
        self.clients = []

        self.lock = threading.Lock()

    def create_token(self, host):
        """
        Attempts to create a token for the given host. If a token exists,
        the existing one will be returned.

        :param host The host address of an authenticating client

        :return A challenge token, new or existing
        """
        # Try get an existing client first. If the client does not exist, we
        # create a new instance for it.
        client = None

        try:
            client = self.get_client_by_host(host)

            logging.debug("Found client matching host '%s', uuid: '%s'",
                host, client.uuid)

        except NoClientFoundError:
            logging.debug("No client matching host '%s', creating a new one", 
                host)

            client = AuthenticatedClient(host)

            with self.lock:
                self.clients.append(client)

        except:
            logging.exception("Unknown exception obtaining client object")
        
        finally:
            logging.debug("Created token for '%s'. uuid: %s, token: %s", 
                host, client.uuid, client.token)
            return client.token

    def authenticate_token(self, token):
        """
        Authenticates a client's token. If the token exists in our cache, then 
        we can simply return the matching UID. If no match is found, raise
        an exception.

        :param token The token to authenticate

        :return The UUID matching the token

        :raises InvalidAuthenticationTokenError When the token is invalid
        """
        
        try:
            client = self.get_client_by_token(token)

            return client.uuid

        except NoClientFoundError:
            raise InvalidAuthenticationTokenError("")

    def get_client_by_host(self, host):
        with self.lock:
            for c in self.clients:
                if c.host == host:
                    return c

            raise NoClientFoundError(
                    "No client found matching host '%s'" % host
                )

    def get_client_by_token(self, token):
        with self.lock:
            for c in self.clients:
                if c.token == token:
                    return c

            raise NoClientFoundError(
                    "No client found matching token '%s'" % token
                )
class AuthenticationServerHandler(SocketServer.BaseRequestHandler):
    """
    Handles authentication attempts. Note that this is a TCP stream - the
    connection remains open until either end hangs up. 

    An authentication attempt is in the form:
    \x01\x00

    A response is in the form:
    \x01\x00<challenge_token>\x00<receiver ip>\x00<receiver port>\x00

    No additional parameters are required, and the source address must be
    whitelisted. TCP source is not spoofable like UDP sources (but can
    be manipulated in other malicious ways such as MITM attacks).
    """
    def __init__(self, request, client_address, server):
        SocketServer.BaseRequestHandler.__init__(self, request, 
            client_address, server)

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

            self.request.send("\x01\x00%s\x00%s\x00%s\x00" % (
                        self.server.authenticator.create_token(
                                self.client_address[0]
                            ),
                        self.server.receiver_address[0],
                        self.server.receiver_address[1]
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
                 receiver_address,
                 handler = AuthenticationServerHandler):
        # Allow binding to the same address if the app didn't exit cleanly
        self.allow_reuse_address = True
        # Ensure request threads are terminated when the application exits
        self.daemon_threads = True

        SocketServer.TCPServer.__init__(self, server_address, handler)

        self.authenticator = authenticator
        self.receiver_address = receiver_address

    def verify_request(self, request, client_address):
        chost, cport = client_address

        allowed = chost in CLIENT_WHITELIST

        logging.debug("Verifying request from '%s'. Allowed: %s", 
            chost, allowed)

        return allowed

class SimpleAuthenticationClient(object):
    """
    A basic implementation of a client which authenticates with the server and
    stores the retrieved token and receiver address.
    """
    def __init__(self, server_address):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.server_address = server_address

        self.authenticated = False
        self.connected = False

        self.token = None
        self.receiver_address = None

    def authenticate(self):
        if self.authenticated:
            return

        self._connect()

        # Send auth code
        self.socket.send("\x01\x00")

        # Wait for response
        resp = self.socket.recv(128)

        # print repr(resp)
        resp = resp.split("\x00")

        if len(resp) > 0:
            token, r_host, r_port = resp[1:4]

            self.token = token
            self.receiver_address = (r_host, int(r_port))

            print "Succesfully authenticated! Token: %s, recv address: %s" % (
                token, self.receiver_address)

            self.authenticated = True

    def _connect(self):
        if not self.connected:
            self.socket.connect(self.server_address)

            self.connected = True
