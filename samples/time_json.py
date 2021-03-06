from webpie import WPApp, WPHandler
import time, json

class Handler(WPHandler):
    
    def time(self, req, relpath, **args):
        t = time.time()
        return json.dumps({
            "epoch":    t,
            "text": time.ctime(t)
        }) + "\n", "text/json"
        
WPApp(Handler).run_server(8080)