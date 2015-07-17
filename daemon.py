"""
daemon.py

This is the main application server. We run the authentication server, video
feed receiver, relay transmitter and client-view server as child threads of
the application.

The Firefly daemon aims to provide a distribution network for the video
feed obtained by the Phoenix multicopter. By using such a network, we 
can show the feed not only to any personnel on-site, but also any
remote personnel such as the operating chief. 
"""


import logging
import threading
import os
import sys
import time


from pprint import pprint

import settings

import authentication
import receiver
import relay
import observer

if __name__ == "__main__":
    authenticator = authentication.Authenticator()

    auth_server_address = (
        settings.authentication["host"], 
        settings.authentication.port
    )

    auth_server = authentication.AuthenticationServer(auth_server_address, 
        authenticator)
    #relay_server = relay.Rela

    receiver_server_address = (
        settings.receiver.host,
        settings.receiver.port
    )

    receiver_server = receiver.ReceiverServer(receiver_server_address, 
        authenticator)

    recv_thread = threading.Thread(target = receiver_server.serve_forever)
    recv_thread.daemon = True

    try:
        recv_thread.start()

        auth_server.serve_forever()

    except KeyboardInterrupt:
        # Exit cleanly
        print "KeyboardInterrupt. Exiting"

    except:
        logging.exception("Unknown exception in main thread. Exiting")

        quit()
