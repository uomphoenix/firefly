import socket

from pprint import pprint

server_address = ('192.168.101.129', 56789)

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

s.connect(server_address)

to_send = "\x01\x00"
print "Sending %s to %s" % (repr(to_send), server_address)
s.send(to_send)

data = s.recv(128)

print "Received '%s' in response" % (repr(data),)
print "Data as string: %s" % (data,)
