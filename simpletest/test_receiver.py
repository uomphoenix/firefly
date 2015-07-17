import socket
from pprint import pprint

server_address = ('192.168.101.129', 56790)

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

s.connect(server_address)


# First is a failure send (i.e. invalid token). Note that we don't get a
# response to these datagrams, as clients that send frames via UDP do
# not expect a response, and responding to invalid frames is a potential
# DDOS avenue.
to_send = "INVALID_CHALLENGE\x00TEST_FRAME\x00"
print "Sending %s to %s" % (repr(to_send), server_address)
s.send(to_send)

# Next, send with a valid token
to_send = "TEST\x00TEST_FRAME\x00"
print "Sending %s to %s" % (repr(to_send), server_address)
s.send(to_send)
