"""
relay.py

The relay module enables the current daemon instance to forward frames received
by the receiver to other instances of the daemon. This lets us establish a
decentralised distribution method, as well as the ability to run the service
in multiple locations. Such ability is necessary for local distribution on
the scene, as well as remotely for various personnel.
"""

import socket
