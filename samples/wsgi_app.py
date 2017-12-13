from wsgi_py import WSGIApp, WSGIHandler, Application, run_server, Response

class MyApp(WSGIApp):
    pass
    
class MyHandler(WSGIHandler):

    def env(self, request, relpath, **args):
        resp_lines = (
            "%s = %s\n" % (k, v) for k, v in request.environ.items()
            )
        return Response(app_iter = resp_lines, content_type="text/plain")
        
app = Application(MyApp, MyHandler)

run_server(8001, app)
