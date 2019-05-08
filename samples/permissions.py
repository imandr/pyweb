# permissions.py
from webpie import WebPieApp, WebPieHandler, run_server, webmethod
import time

class H_methods(WebPieHandler):	

    _Methods = ["hello"]		

    def hello(self, request, relpath):				
	    return "Hello, World!\n"	

    def wrong(self, request, relpath):
        return "This should never happen\n"
        
class H_decorators(WebPieHandler):

    @webmethod()
    def hello(self, request, relpath):				
	    return "Hello, World!d\n"	

    @webmethod()
    def wrong(self, request, relpath):
        return "This should never happen\n"

class H_permissions(WebPieHandler):

    def _roles(self, request, relpath):
        return [relpath]

    @webmethod(["read","write"])
    def read_write(self, request, relpath):				
	    return "Read/write access granted\n"	

    @webmethod(["read"])
    def read_only(self, request, relpath):
        return "Read access granted\n"

class H_open(WebPieHandler):

    def hello(self, request, relpath):				
	    return "Hello, World!\n"	

    def wrong(self, request, relpath):
        return "This should never happen\n"

class Top(WebPieHandler):

    def __init__(self, req, app, path):
        WebPieHandler.__init__(self, req, app, path)

        self.o = H_open(req, app, path)
        self.m = H_methods(req, app, path)
        self.d = H_decorators(req, app, path)
        self.p = H_permissions(req, app, path)

application = WebPieApp(Top, strict=True)
application.run_server(8080)

