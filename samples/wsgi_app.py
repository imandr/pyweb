from webpie import WebPieApp, WebPieHandler, run_server, Response

class MyApp(WebPieApp):
    pass
    
class SubHandler(WebPieHandler):
    pass
    
class TopHandler(WebPieHandler):
    
    def __init__(self, request, app, path):
        WebPieHandler.__init__(self, request, app, path)
        self.A = SubHandler(request, app, "/A")
    
app = MyApp(TopHandler)

run_server(8001, app)
