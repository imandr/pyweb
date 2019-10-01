from webpie import WebPieApp, WebPieHandler, atomic

class MyApp(WebPieApp):
    
    RecordSize = 10
    
    def __init__(self, root_class):
        WebPieApp.__init__(self, root_class)
        self.Record = []
        
    @atomic
    def add(self, value):
        if value in self.Record:
            self.Record.remove(value)
        self.Record.insert(0, value)
        if len(self.Record) > self.RecordSize:
            self.Record = self.Record[:self.RecordSize]
        
    @atomic
    def find(self, value):
        try:    i = self.Record.index(value)
        except ValueError:
            return "not found"
        self.Record.pop(i)
        self.Record.insert(0, value)
        return str(i)
        
class Handler(WebPieHandler):
    
    def add(self, req, relpath, **args):
        return self.App.add(relpath)
        
    def find(self, req, relpath, **args):
        return self.App.find(relpath)
        
application = MyApp(Handler)
application.run_server(8002)

