"""
A simple test which reads from a video file and sends the frames
"""

import socket
import time
import math
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

#video = cv2.VideoCapture('lepton_6.avi')
#video = cv2.VideoCapture('test.mp4')
video = cv2.VideoCapture('test_hd.mkv')

framerate = video.get(5)

frame_cap = 999999999999
frames_sent = 0

# This should NEVER be bigger than 8192
MAX_PACKET_SIZE = 4096

"""<challenge>\x00<seq num>\x00<max fragments>\x00<fragment num>\x00<frame>\x00"""

while True:
    success, image = video.read()

    if not success:
        print "Unable to read image from the video file"
        break

    ret, frame = cv2.imencode('.jpg', image)

    #print len(frame.tobytes())
    #print repr(frame.tobytes())

    frame = frame.tobytes()
    frame_len = len(frame)
    if frame_len > MAX_PACKET_SIZE:
        # need to split the frame into fragments
        num_fragments = int(math.ceil(1.0*frame_len/MAX_PACKET_SIZE))
        print "Splitting frame into %d fragments" % num_fragments

        fragment_len_sent = 0
        curr_index = 0
        end_index = MAX_PACKET_SIZE
        for i in range(num_fragments):
            if end_index > frame_len:
                end_index = frame_len

            print "Frame %s indexing range: %s to %s, fragment: %d" % (
                    frames_sent, curr_index, end_index, i
                )

            fragment = frame[curr_index:end_index]
            print "length of fragment: %s" % len(fragment)

            to_send = "%s\x00%s\x00%s\x00%s\x00%s\x00" % (
                auth.token, frames_sent, num_fragments, i, fragment
            )

            #print "Sending %s to %s" % (repr(to_send), auth.receiver_address)
            c.send(to_send)

            fragment_len_sent += len(fragment)

            curr_index = end_index
            end_index += MAX_PACKET_SIZE

        print "length sent: %s, frame len: %s" % (fragment_len_sent, frame_len)

    else:
        to_send = "%s\x00%s\x00%s\x00%s\x00%s\x00" % (auth.token, frames_sent, 1, 1, frame)

        #print "Sending %s to %s" % (repr(to_send), auth.receiver_address)
        c.send(to_send)

    frames_sent += 1
    if frames_sent >= frame_cap:
        break

    time.sleep(1/framerate)

print "Frames sent: " + str(frames_sent)

c.close()

video.release()
