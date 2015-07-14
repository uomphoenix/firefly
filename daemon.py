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


if __name__ == "__main__":
    pass
