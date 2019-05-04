from webpie import atomic, WebPieApp, WebPieHandler, run_server, Response
import time

class MyApp(WebPieApp):
    
    def __init__(self, root_class):
        WebPieApp.__init__(self, root_class)
        self.Count = 0
        
class MyHandler(WebPieHandler):

    @atomic
    def hello(self, request, relpath, t=3):
        c = self.App.Count
        t = int(t)
        time.sleep(t)
        assert self.App.Count == c
        self.App.Count += 1
        return Response("Request count is now %d\n" % (self.App.Count,), 
            content_type="text/plain")
        
app = MyApp(MyHandler)

run_server(8001, app)
