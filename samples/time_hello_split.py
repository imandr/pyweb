# time_hello_split.py
from webpie import WebPieApp, WebPieHandler
import time

class Greeter(WebPieHandler):						

	def hello(self, request, relpath):				
		return "Hello, World!\n"					

class Clock(WebPieHandler):						

	def time(self, request, relpath):				# 1
		return time.ctime()+"\n", "text/plain"		# 2

class TopHandler(WebPieHandler):

	def __init__(self, *params, **kv):
		WebPieHandler.__init__(self, *params, **kv)
		self.greet = Greeter(*params, **kv)
		self.clock = Clock(*params, **kv)

	def version(self, request, relpath):
		return "1.0.2"


application = WebPieApp(TopHandler)
application.run_server(8080)
