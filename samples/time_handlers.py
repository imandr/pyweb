# time_returns.py

from webpie import WebPieApp, WebPieHandler, Response, webmethod, WebPieStaticHandler
import time, json

class CallableHandler(WebPieHandler):
    
    def __call__(self, request, relpath, **args):
        return (relpath or "hi there")+"\n", "text/plain"
        
class RegularHandler(WebPieHandler):

    _Strict = False
    
    @webmethod()
    def time(self, request, relpath, **args):
        return time.ctime()+"\n"
        
class TopHandler(WebPieHandler):
    
    RouteMap = [
        ("Responder",       "constant text\n"),
        ("Lambda",          lambda request, relath, text="(empty)": "text was: %s" % (text,)),
        ("Callable",        CallableHandler),
        ("robots.txt",      "User-agent: *\nDisallow: /"),
    ]
    
    def __init__(self, request, app, path):
        WebPieHandler.__init__(self, request, app, path)
        self.Regular = RegularHandler(request, app, path)
        self.static = WebPieStaticHandler("static")
        
    def __call__(self, request, relpath, **args):
        return "Args:\n"+"\n".join(["%s=%s" % (k,v) for k, v in args.items()])
        
    def top(self, request, relpath, **args):
        return "top method"

        
WebPieApp(TopHandler).run_server(8080)
