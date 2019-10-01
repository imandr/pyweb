from webpie import WebPieApp, WebPieHandler, atomic

class MyApp(WebPieApp):
    
    def __init__(self, root_class):
        WebPieApp.__init__(self, root_class)
        self.Memory = {}
    
class Handler(WebPieHandler):
    
    @atomic
    def set(self, req, relpath, name=None, value=None, **args):
        self.App.Memory[name]=value
        
    @atomic
    def get(self, req, relpath, name=None, **args):
        return self.App.Memory.get(name, "(undefined)")
        
application = MyApp(Handler)
application.run_server(8002)

