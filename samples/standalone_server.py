from webpie import WebPieApp
from webpie import WebPieHandler 
from webpie import run_server
from webpie import Response

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
        
    
app = MyApp(TopHandler)

print("Server is listening at port 8001...")
run_server(8001, app)
