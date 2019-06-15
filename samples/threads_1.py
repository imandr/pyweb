from webpie import WebPieApp, WebPieHandler, run_server, Response, app_synchronized

class MyApp(WebPieApp):
    
    def __init__(self, root_class):
        WebPieApp.__init__(root_class)
        self.Memory = {}
    
class Handler(WebPieHandler):
    
    @app_synchronized
    def set_value(self, req, relpath, name=None, value=None, **args):
        self.App.Memory[name]=value
        
    @app_synchronized
    def get_value(self, req, relpath, name=None, **args):
        return self.App.Memory.get(name, "(undefined)")
        
    
        
        
    
application = MyApp(TopHandler)

