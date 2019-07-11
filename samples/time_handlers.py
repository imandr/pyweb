# time_returns.py

from webpie import WebPieApp, WebPieHandler, Response
import time, json

class CallableHandler(WebPieHandler):
    
    def __call__(self, request, relpath, **args):
        print args
        return (relpath or "hi there")+"\n", "text/plain"
        
class RegularHandler(WebPieHandler):
    
    def time(self, request, relpath, **args):
        return time.ctime()+"\n"
        
class TopHandler(WebPieHandler):
    
    def __init__(self, request, app):
        WebPieHandler.__init__(self, request, app)
        self.Callable = CallableHandler(request, app)
        self.Regular = RegularHandler(request, app)
        self.addHandler("Responder", "constant text\n")
        self.addHandler("Lambda", lambda request, relath, text="hello": "text was: %s" % (text,))

        
WebPieApp(TopHandler).run_server(8080)
