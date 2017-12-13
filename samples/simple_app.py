from pyweb import HTTPServer, PyWebApp, PyWebHandler, Response
from threader import synchronized

class MyApp(PyWebApp):

    def __init__(self, handlerclass):
        PyWebApp.__init__(self, handlerclass)
        self.Count = 0

    @synchronized
    def count(self):
        c = self.Count + 1
        self.Count = c
        return c
        
    
class MyHandler(PyWebHandler):

    def env(self, request, relpath, **args):
        resp_lines = (
            "%s = %s\n" % (k, v) for k, v in request.environ.items()
            )
        return Response(app_iter = resp_lines, content_type="text/plain")
        
    def count(self, request, relpath, **args):
        return Response("%d" % (self.App.count(),), content_type="text/plain")
        
app = MyApp(MyHandler)
hs = HTTPServer(8001, app)
hs.start()
hs.join()
