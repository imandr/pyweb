# hello_world_server.py
from webpie import WebPieApp, WebPieHandler, run_server
import time

class MyHandler(WebPieHandler):						

	def hello(self, request, relpath):				
		return "Hello, World!\n"					

application = WebPieApp(MyHandler)
application.run_server(8080)

