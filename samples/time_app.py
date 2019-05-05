# time_app.py
from webpie import WebPieApp, WebPieHandler
import time

class MyHandler(WebPieHandler):						

	def hello(self, request, relpath):				
		return "Hello, World!\n"					

	def time(self, request, relpath):				# 1
		return time.ctime()+"\n", "text/plain"		# 2

application = WebPieApp(MyHandler)
application.run_server(8080)
