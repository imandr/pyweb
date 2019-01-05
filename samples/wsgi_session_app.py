from webpie import WebPieSessionApp, WebPieHandler, run_server, Response

class MyApp(WebPieSessionApp):
    pass
    
class MyHandler(WebPieHandler):

    def data(self, request, relpath, name=None, value=None):
        if value is None:
            return Response(self.session[name], content_type="text/plain")
        else:
            self.session[name] = value
            return Response("OK", content_type="text/plain")

    def clear(self, request, relpath):
        self.session.clear()
        return Response("OK", content_type="text/plain")
        
    def bulk(self, request, relpath, name=None, value=None):
        if value is None:
            return Response(self.session.bulk[name], content_type="text/plain")
        else:
            self.session.bulk[name] = value
            return Response("OK", content_type="text/plain")
        

    def session_info(self, request, relpath):       
        sid = self.session.session_id
        items = self.session.items()
        return Response(app_iter = 
            [
                "Session id = %s\nData:\n" % (sid,),
            ] + ["%s: %s\n" % item for item in items],
            content_type="text/plain"
        )
        
        
app = MyApp(MyHandler)

run_server(8001, app)
