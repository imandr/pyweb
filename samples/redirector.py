# redirector.py
from webpie import WPApp, WPHandler
import sys

class Redirector(WPHandler):
    
    def __call__(self, request, relpath, **args):
        new_url = self.App.URLHead + request.path_qs
        self.redirect(new_url)

class RedirectorApp(WPApp):
    
    def __init__(self, url_head, handler):
        WPApp.__init__(self, handler)
        self.URLHead = url_head

if not sys.argv[1:]:
    print ("Usage: python redirector.py <new URL head>")
    sys.exit(2)

url_head = sys.argv[1]
RedirectorApp(url_head, Redirector).run_server(8080)
        