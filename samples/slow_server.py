# time_app.py
from webpie import WebPieApp, WebPieHandler
import time

class MyHandler(WebPieHandler):						

    def data(self, request, relpath, lines=10, line_delay=1):
        return (time.sleep(line_delay) or "line {}\n".format(i,) for i in range(int(lines)))

application = WebPieApp(MyHandler)
application.run_server(8080)


