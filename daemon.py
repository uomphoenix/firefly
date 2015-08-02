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
import caching
import receiver
import relay
import observer

logging.basicConfig(level = logging.DEBUG)

if __name__ == "__main__":
    logging.info("Initializing Firefly daemon")

    # Initialize shared objects first
    authenticator = authentication.Authenticator()
    feed_cache = caching.FeedCache(settings.receiver.cache_size)

    # Instantiate server objects
    ## Receiver
    receiver_server_address = (
        settings.receiver.host,
        settings.receiver.port
    )

    receiver_server = receiver.ReceiverServer(receiver_server_address, 
        authenticator, feed_cache)

    logging.info("Receiver server listening on %s:%s" % \
        receiver_server.server_address)

    ## Auth server
    auth_server_address = (
        settings.authentication.host, 
        settings.authentication.port
    )

    auth_server = authentication.AuthenticationServer(auth_server_address, 
        authenticator, receiver_server.server_address)
    
    logging.info("Authentication server listening on %s:%s" % \
        auth_server.server_address)

    ## Observer server
    observer_server_address = (
        settings.observer.host,
        settings.observer.port
    )

    observer_server = observer.ObserverServer(observer_server_address,
        feed_cache)

    logging.info("Observer server listening on %s:%s" % \
        observer_server_address)

    # Create threads and set thread properties
    recv_thread = threading.Thread(target = receiver_server.serve_forever)
    recv_thread.daemon = True

    auth_thread = threading.Thread(target = auth_server.serve_forever)
    auth_thread.daemon = True

    try:
        logging.info("Starting receiver thread ...")
        recv_thread.start()

        logging.info("Starting auth thread ...")
        auth_thread.start()

        logging.info("Running observer server in main thread ...")
        observer_server.run()

    except KeyboardInterrupt:
        # Exit cleanly
        print "KeyboardInterrupt. Exiting"
        servers = [ auth_server, receiver_server, observer_server ]
        
        for s in servers:
            # Stop listening & close sockets
            s.shutdown()
            s.server_close()

    except:
        logging.exception("Unknown exception in main thread. Exiting")

        quit()
