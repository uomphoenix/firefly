# What is Firefly?
Firefly is a daemon written in Python (2.7) to facilitate the distribution of
live video camera footage to many users. The daemon receives frames of the
video feed encoded as JPEG, and then caches them for realtime viewing by
clients. 

A simple HTTP MPEG streaming protocol is used, whereby frames are
successively sent with each new frame replacing the last, simulating a video
stream. This is not the most efficient method, but it is well supported by
almost all devices, allowing cross-platform viewing with minimal work. The 
alternative would be to encode the video feed in realtime and serve it 
either using custom software (HTML5 video, Flash, specialised app, etc).

HTTP streams can also be viewed in popular video players such as VLC and 
gstreamer.

# Installation
Firefly runs with Python 2.6 or 2.7, it may work on Python 3 but it has not
been tested. The following packages are also required:

+ tornado (A fast asynchronous webserver framework)
+ futures (A backport of the Py3 futures module)

Once the packages are installed, all that is required is this repository.

# Configuration
Basic configuration is supplied in the file `settings.py`, which has 
self-explanatory options and basic initial values.

To whitelist your client (which sends the video feeds), you must enter
the host address in the `settings.authentication.whitelist` list.

# Running Firefly
To run Firefly, simply execute `daemon.py` once the desired options have been set
in `settings.py`. 

A simple test (with a video file) is included in `simpletest/test_with_video.py`.
To run the test, OpenCV 2.4.9+ and NumPy packages are required. Note that this
is an extremely low resolution test file, which is nice for testing with a small
footprint. 

The basic idea is to authenticate (using the 
`authentication.SimpleAuthenticationClient`), and then send frames acquired
from any source (such as a video camera) to the receiver address which is
received upon authentication and set as an attribute in the object.

Once frames are being received by the daemon's receiver module, they can
be viewed by navigating to /feed/<identifer> on the observer's listen
address. Alternatively, the root path on the observer will serve a page
listing all existing feeds. Only the most recent frames (based on the cache
size) will be served in the live stream. 10 seconds of sending no new frames
will disconnect a client (configurable in `observerhandlers.FrameHelper`).

# Limitations/NYI
+ Some frame sources which have extremely high resolutions are not compatible 
  with Firefly at this point in time. This is because said frames are too large
  to be sent in a single packet, and cause a network overflow. Since the
  receiver does not currently support split-frame packets (i.e. multiple
  packets for a single frame), these sources are not supported.

+ Currently feeds will never expire, and require a restart of the daemon to
  clear existing caches

+ Video feeds are not currently written to disk, so there is no local storage.
  This is a feature that we are aiming to implement ASAP.

