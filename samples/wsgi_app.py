from webpie import WSGIApp, WSGIHandler, run_server, Response

class MyApp(WSGIApp):
    pass
    
class SubHandler(WSGIHandler):
    pass
    
class TopHandler(WSGIHandler):
    
    def __init__(self, request, app, path):
        WSGIHandler.__init__(self, request, app, path)
        self.A = SubHandler(request, app, "/A")
    
app = MyApp(TopHandler)

run_server(8001, app)
