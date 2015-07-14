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
etc.

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
