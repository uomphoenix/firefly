"""
This is a simple script to authenticate, obtain a token and then send test
frames to the daemon. As there is no hardcoded test token anymore, we cannot
use the basic receiver test.
"""

import socket
import sys
sys.path.append('..') # required to import from upper directory

import authentication
from pprint import pprint

server_address = ('192.168.101.129', 56789)


# Test using the simple auth client in the authentication module
auth = authentication.SimpleAuthenticationClient(server_address, "TEST STREAM")

auth.authenticate()

c = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

c.connect(auth.receiver_address)

to_send = "%s\x00TEST_FRAME\x00" % auth.token
print "Sending %s to %s" % (repr(to_send), auth.receiver_address)
c.send(to_send)

c.close()
