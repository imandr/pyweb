from pyweb import PyWebSessionApp, PyWebHandler, run_server, Response

class MyApp(PyWebSessionApp):
    pass
    
class MyHandler(PyWebHandler):

    def set(self, request, relpath, name=None, value=None):
        self.App.session[name] = value
        return Response("OK", content_type="text/plain")

    def get(self, request, relpath, name=None):
        return Response(self.App.session.get(name, "undefined"), 
                content_type="text/plain")
                
    def clear(self, request, relpath):
        self.App.session.clear()
        return Response("OK", content_type="text/plain")

    def session_info(self, request, relpath):       
        sid = self.App.session.session_id
        items = self.App.session.items()
        return Response(app_iter = 
            [
                "Session id = %s\nData:\n" % (sid,),
            ] + ["%s: %s\n" % item for item in items],
            content_type="text/plain"
        )
        
        
app = MyApp(MyHandler)

run_server(8001, app)
