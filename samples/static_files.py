from webpie import WebPieApp
from webpie import WebPieHandler, WebPieStaticHandler
from webpie import run_server
from webpie import Response

class MyApp(WebPieApp):
    pass
    
class TopHandler(WebPieHandler):
    
    def __init__(self, request, app, path):
        WebPieHandler.__init__(self, request, app, path)
        self.static = WebPieStaticHandler(request, app, "/static")
        
    def hello(self, request, relpath, **args):
        return "Hello world!", "text/plain"
        
app = MyApp(TopHandler)

print("Server is listening at port 8001...")
run_server(8001, app)
