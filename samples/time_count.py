# time_count.py
from webpie import WebPieApp, WebPieHandler
import time

class Handler(WebPieHandler):						

	def time(self, request, relpath):		
		self.App.Counter += 1
		return time.ctime()+"\n", "text/plain"
	
	def count(self, request, relpath): 
		return str(self.App.Counter)+"\n"


class App(WebPieApp):

	def __init__(self, handler_class):
		WebPieApp.__init__(self, handler_class)
		self.Counter = 0

application = App(Handler)
application.run_server(8080)
