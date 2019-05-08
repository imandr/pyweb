# time_index.py

from webpie import WebPieApp, WebPieHandler
import time

class MyHandler(WebPieHandler):						

	def time(self, request, relpath):
		return time.ctime()+"\n", "text/plain"	

	def index(self, request, relpath):
		return "[index] "+time.ctime()+"\n", "text/plain" 

WebPieApp(MyHandler).run_server(8080)
