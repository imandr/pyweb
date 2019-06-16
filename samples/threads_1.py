from webpie import WebPieApp, WebPieHandler, app_synchronized

class MyApp(WebPieApp):
    
    def __init__(self, root_class):
        WebPieApp.__init__(self, root_class)
        self.Memory = {}
    
class Handler(WebPieHandler):
    
    @app_synchronized
    def set(self, req, relpath, name=None, value=None, **args):
        print "value=%s %s" % (type(value), value)
        self.App.Memory[name]=str(value)
        return "OK"
        
    @app_synchronized
    def get(self, req, relpath, name=None, **args):
        value = self.App.Memory.get(name, "(undefined)")
        print value
        return value
        
application = MyApp(Handler)
application.run_server(8001)

