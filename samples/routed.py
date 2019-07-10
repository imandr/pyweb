from webpie import WebPieApp, WebPieHandler

def robots(request, relpath, **args):
        return "reject"

class MyHandler(WebPieHandler):
    def __init__(self, request, path):
        WebPieHandler.__init__(self, request, path)
        self.addHandler("robots.txt", "reject", 400)

WebPieApp(MyHandler).run_server(8080)