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

s.close()

if len(data) > 0:
    auth_code, challenge_token, host, port, tail = data.split("\x00")
    port = int(port)

    receiver_address = (host,port)
    c = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    c.connect(receiver_address)

    to_send = "%s\x00TEST_FRAME\x00" % challenge_token
    print "Sending %s to %s" % (repr(to_send), receiver_address)
    c.send(to_send)

    c.close()
