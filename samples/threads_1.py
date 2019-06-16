from webpie import WebPieApp, WebPieHandler, app_synchronized

class MyApp(WebPieApp):
    
    def __init__(self, root_class):
        WebPieApp.__init__(self, root_class)
        self.Memory = {}
    
class Handler(WebPieHandler):
    
    @app_synchronized
    def set(self, req, relpath, name=None, value=None, **args):
        self.App.Memory[name]=value
        
    @app_synchronized
    def get(self, req, relpath, name=None, **args):
        return self.App.Memory.get(name, "(undefined)")
        
application = MyApp(Handler)
application.run_server(8002)

