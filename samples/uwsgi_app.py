from webpie import WebPieApp, WebPieHandler, run_server, Response

class MyApp(WebPieApp):
    pass
    
class SubHandler(WebPieHandler):
    pass
    
class TopHandler(WebPieHandler):
    
    def __init__(self, request, app, path):
        WebPieHandler.__init__(self, request, app, path)
        self.A = SubHandler(request, app, "/A")
        
    def hello(self, request, relpath, **args):
        return "Hello world!", "text/plain"
        
    def post(self, request, relpath, **args):
        return "Body length={}".format(len(request.body))
        
    
application = MyApp(TopHandler)

