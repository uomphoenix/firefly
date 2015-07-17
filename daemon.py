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

logging.basicConfig(level = logging.DEBUG)

if __name__ == "__main__":
    logging.info("Initializing Firefly daemon")
    authenticator = authentication.Authenticator()

    auth_server_address = (
        settings.authentication["host"], 
        settings.authentication.port
    )

    auth_server = authentication.AuthenticationServer(auth_server_address, 
        authenticator)
    
    logging.info("Authentication server listening on %s:%s" % \
        auth_server.server_address)

    receiver_server_address = (
        settings.receiver.host,
        settings.receiver.port
    )

    receiver_server = receiver.ReceiverServer(receiver_server_address, 
        authenticator)

    logging.info("Receiver server listening on %s:%s" % \
        receiver_server.server_address)

    recv_thread = threading.Thread(target = receiver_server.serve_forever)
    recv_thread.daemon = True

    try:
        logging.info("Starting receiver thread ...")
        recv_thread.start()

        logging.info("Running authentication server in main thread ...")
        auth_server.serve_forever()

    except KeyboardInterrupt:
        # Exit cleanly
        print "KeyboardInterrupt. Exiting"
        servers = [ auth_server, receiver_server ]
        
        for s in servers:
            # Stop listening & close sockets
            s.shutdown()
            s.server_close()

    except:
        logging.exception("Unknown exception in main thread. Exiting")

        quit()
