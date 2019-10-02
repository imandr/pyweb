from webpie import WebPieApp, WebPieHandler

class MyApp(WebPieApp):
    
    def __init__(self, root_class):
        WebPieApp.__init__(self, root_class)
        self.Memory = {}
    
class Handler(WebPieHandler):
    
    def set(self, req, relpath, name=None, value=None, **args):
        with self.App:
            self.App.Memory[name]=value
        return "OK\n"
        
    def get(self, req, relpath, name=None, **args):
        with self.App:
            return self.App.Memory.get(name, "(undefined)") + "\n"
        
application = MyApp(Handler)
application.run_server(8002)

