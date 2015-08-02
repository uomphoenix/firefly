"""
observer.py

Handles viewing client interactions, and distributes frames as necessary to
clients in order to deliver a live stream.
"""

import logging

from settings import observer as obs_settings

try:
    import tornado
    import tornado.options
    import tornado.web
    import tornado.ioloop
    import tornado.escape
except ImportError:
    print """The Firefly daemon requires `tornado` for serving web streams. 
    Install tornado using `pip install tornado`, or visit http://www.tornadoweb.org/
    """
    quit()

import observerhandlers

class ObserverApplication(tornado.web.Application):
    def __init__(self, feed_cache):
        handlers = [
            (r"/", observerhandlers.RootHandler),
        ]

        settings = {
            "debug": True,
            "autoreload": True
        }

        super(ObserverApplication, self).__init__(handlers, **settings)

class ObserverServer(object):
    def __init__(self, server_address, feed_cache):
        self.feed_cache = feed_cache
        
        self.application = ObserverApplication(feed_cache)
        self.application.listen(server_address[1], server_address[0])

        self.server_address = server_address

    def run(self):
        tornado.ioloop.IOLoop.instance().start()

    def shutdown(self):
        tornado.ioloop.IOLoop.instance().stop()

    def server_close(self):
        pass

if __name__ == "__main__":
    tornado.options.parse_command_line()

    print "test"


    logging.debug("Running observer in standalone debug mode")

    s = ObserverServer(('127.0.0.1', 12345), None)

    try:
        s.run()
    except KeyboardInterrupt:
        s.shutdown()
    except:
        logging.exception("Uncaught exception")
        quit()
