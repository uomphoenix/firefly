"""
A simple test which reads from a video file and sends the frames
"""

import socket
import time
import sys
sys.path.append('..') # required to import from upper directory

import cv2

import authentication
from pprint import pprint

server_address = ('192.168.101.129', 56789)


# Test using the simple auth client in the authentication module
auth = authentication.SimpleAuthenticationClient(server_address, "TEST_STREAM")

auth.authenticate()

c = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

c.connect(auth.receiver_address)

video = cv2.VideoCapture('lepton_6.avi')
#video = cv2.VideoCapture('test.mp4')

framerate = video.get(5)

frame_cap = 999999999999
frames_sent = 0

while True:
    success, image = video.read()

    if not success:
        print "Unable to read image from the video file"
        break

    ret, frame = cv2.imencode('.jpg', image)

    #print len(frame.tobytes())
    #print repr(frame.tobytes())

    to_send = "%s\x45\x45%s" % (auth.token, frame.tobytes())

    print "Sending %s to %s" % (repr(to_send), auth.receiver_address)
    c.send(to_send)

    frames_sent += 1
    if frames_sent >= frame_cap:
        break

    time.sleep(1/framerate)

print "Frames sent: " + str(frames_sent)

c.close()

video.release()
