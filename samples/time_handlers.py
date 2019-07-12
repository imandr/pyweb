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
    
    RouteMap = [
        ("Responder",       "constant text\n"),
        ("Lambda",          lambda request, relath, text="hello": "text was: %s" % (text,)),
        ("Callable",        CallableHandler)
    ]
    
    def __init__(self, request, app, path):
        WebPieHandler.__init__(self, request, app, path)
        self.Regular = RegularHandler(request, app, path)
        
    def __call__(self, request, relpath, **args):
        return "Args:\n"+"\n".join(["%s=%s" % (k,v) for k, v in args.items()])

        
WebPieApp(TopHandler).run_server(8080)
