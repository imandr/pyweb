from webpie import atomic, WSGIApp, WSGIHandler, Application, run_server, Response
import time

request_count = 0

class MyApp(WSGIApp):
    pass
    
class MyHandler(WSGIHandler):

    @atomic
    def hello(self, request, relpath, t=3):
        global request_count
        t = int(t)
        time.sleep(t)
        request_count += 1
        return Response("Request count is now %d" % (request_count,), 
            content_type="text/plain")
        
app = Application(MyApp, MyHandler)

run_server(8001, app)
