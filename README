# WebPie

WebPie (another way of spelling web-py) is a web application development framework for Python based on the WSGI standard.
WebPie makes it simple to develop thread-safe object-oriented web applications.

## Hello World in WebPie

Here is the simplest web application you can write:

```
# hello_world.py
from webpie import WebPieApp, WebPieHandler			# 1
class MyHandler(WebPieHandler):						# 2
	def hello(self, request, relpath):				# 3
		return "Hello, World!\n"					# 4
application = WebPieApp(MyHandler)					# 5
```

What did we just write ? Let's go over the code line by line.

1. We need at least 2 classes to import - WebPieApp and WebPieHandler. 
2. We created class MyHandler, which will handle HTTP requests. It has to be a subclass of WebPieHandler class.
3. We defined one web method "hello".
4. It will always return text "Hello, World!"
5. Finally, we created a WSGI application as an instance of WebPieApp class, passing it the MyHandler class as an argument.

Now we can plug our application into any WSGI framework such as uWSGI or Apache httpd, e.g.:

```
uwsgi --http :8080 --wsgi-file hello_world.py
```

now we can try it:

```
$ curl http://localhost:8080/hello
Hello world!
$ 
```

If you do not want to use uWSGI or similar framework, you can use WebPie's own HTTP server to publich your application on the web:

```
# hello_world_server.py
from webpie import WebPieApp, WebPieHandler, run_server
import time

class MyHandler(WebPieHandler):						

	def hello(self, request, relpath):				
		return "Hello, World!\n"					

application = WebPieApp(MyHandler)
application.run_server(8080)
```

## URL Structure
Notice that MyHandler class has single method "hello" and it maps to the URL path "hello". This is general rule in WebPie - methods of handler classes map one to one to the elements of URI path. For example, we can add another method to our server called "time":

```
# time_app.py
from webpie import WebPieApp, WebPieHandler
import time

class MyHandler(WebPieHandler):						

	def hello(self, request, relpath):				
		return "Hello, World!\n"					

	def time(self, request, relpath):
		return time.ctime()+"\n"

application = WebPieApp(MyHandler)
application.run_server(8080)
```

Now our handler can handle 2 types of requests, it can say hello and it can tell local time:

```
$ curl http://localhost:8080/hello
Hello, World!
$ curl http://localhost:8080/time
Sun May  5 06:47:15 2019
$ 
```
Notice that handler methods names automatically become parts of the URL path. There is no need (and no other way) to map WebPie methods to URL.

If you want to split your handler into different classes to organize your code better, you can have multiple handler classes in your application. For example, we may want to have one handler which focuses on reporting time and the other which says hello:
```
# time_hello_split.py
from webpie import WebPieApp, WebPieHandler
import time

class HelloHandler(WebPieHandler):						

	def hello(self, request, relpath):				
		return "Hello, World!\n"					

class ClockHandler(WebPieHandler):						

	def time(self, request, relpath):			
		return time.ctime()+"\n", "text/plain"	

class TopHandler(WebPieHandler):

	def __init__(self, *params, **kv):
		WebPieHandler.__init__(self, *params, **kv)
		self.greet = HelloHandler(*params, **kv)
		self.clock = ClockHandler(*params, **kv)


application = WebPieApp(TopHandler)
application.run_server(8080)
```

WebPie application always has single Top Handler (1), which optionally can have other handlers as its members and they can have their own child handlers. This recirsive handler structure maps one-to-one to the URL structure. The URI is simply the path from top handler through its child handlers to the method of one of them:

```
$ curl  http://localhost:8080/clock/time
Sun May  5 07:39:11 2019
$ curl  http://localhost:8080/greet/hello
Hello, World!
$ 
```

For example, to find the method for URI "/clock/time", WebPie starts with top handler, finds its child handler "greet" of class Greeter and then calls its "time" method.

Not only leaf handlers can have methods. For example, any handler can have its own methods. For example:

```
# time_hello_split2.py
from webpie import WebPieApp, WebPieHandler
import time

class HelloHandler(WebPieHandler):						

	def hello(self, request, relpath):				
		return "Hello, World!\n"					

class ClockHandler(WebPieHandler):						

	def time(self, request, relpath):			
		return time.ctime()+"\n", "text/plain"	

class TopHandler(WebPieHandler):

	def __init__(self, *params, **kv):
		WebPieHandler.__init__(self, *params, **kv)
		self.greet = HelloHandler(*params, **kv)
		self.clock = ClockHandler(*params, **kv)
		
	def version(self, request, relpath):
	    return "1.0.3"

application = WebPieApp(TopHandler)
application.run_server(8080)
```

```
$ curl  http://localhost:8080/version
1.0.2
```

## Application and Handler Lifetime

The WebPieApp is created when the web server starts and it exists until the server stops whereas WebPieHandler objects are created for each individual HTTP request. When Handler object is created, it receives the pointer to the App object as its constructor argiment. Also, for convenience, Handler object's App member always pointt to the App object. This allows the App object to keep some persistent information and let Handler objects access it. For example, or clock application can also maintain number of requests it has received:

```
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
```

```
$ curl  http://localhost:8080/time
Sun May  5 08:10:12 2019
$ curl  http://localhost:8080/time
Sun May  5 08:10:14 2019
$ curl  http://localhost:8080/count
2
$ curl  http://localhost:8080/time
Sun May  5 08:10:17 2019
$ curl  http://localhost:8080/count
3
```

Of course the way it is written, our application is not very therad-safe, but we will talk about this later.

## Web Server Methods in Details

The web the WebPie server handler method has 2 fixed arguments and optional keyword arguments.

First argiment is the request object, which encapsulates all the information about the HTTP request. Currently WebPie uses WebOb library Request and Response classes to handle HTTP requests and responses.

Most generally, web server method looks like this:

```
from webpie import WebPieHandler, Response
class Handler(WebPieHandler):

    #...
    def method(self, request, relpath, **url_args):
        # ...
        return Response(...)
```

Method arguments are:
### request
request is WebOb request object
### relpath
Sometimes the URI elements are used as web service method arguments and relpath is the tail of the URI remaining unused after the mapping from URI to the method is done. For example, in our clock example, we may want to use URL like this to specify the field of the current time we want to see:

```
http://localhost:8080/time/month    # month only
http://localhost:8080/time/minute   # minute only
http://localhost:8080/time          # whole day/time
```
Here is the code which does this:

```
from webpie import WebPieApp, WebPieHandler
from datetime import datetime

class MyHandler(WebPieHandler):						

	def time(self, request, relpath):				# 1
		t = datetime.now()
		if not relpath:
			return str(t)+"\n"
		elif relpath == "year":
			return str(t.year)+"\n"
		elif relpath == "month":
			return str(t.month)+"\n"
		elif relpath == "day":
			return str(t.day)+"\n"
		elif relpath == "hour":
			return str(t.hour)+"\n"
		elif relpath == "minute":
			return str(t.minute)+"\n"
		elif relpath == "second":
			return str(t.second)+"\n"

application = WebPieApp(MyHandler)
application.run_server(8080)
```
### url_args
Typically URL includes so called query parameters, e.g.:
```
http://localhost:8080/time?field=minute
```
WebPie always parses query parameters and passes them to the handler method using keyword arguments. For example, we can write the method which extracts fields from current time like this:
```
# time_args.py
from webpie import WebPieApp, WebPieHandler
from datetime import datetime

class MyHandler(WebPieHandler):						

	def time(self, request, relpath, field="all"):		
		t = datetime.now()
		if field == "all":
			return str(t)+"\n"
		elif field == "year":
			return str(t.year)+"\n"
		elif field == "month":
			return str(t.month)+"\n"
		elif field == "day":
			return str(t.day)+"\n"
		elif field == "hour":
			return str(t.hour)+"\n"
		elif field == "minute":
			return str(t.minute)+"\n"
		elif field == "second":
			return str(t.second)+"\n"

WebPieApp(MyHandler).run_server(8080)

```
and then call it like this:
```
$ curl  http://localhost:8080/time
2019-05-05 08:39:49.593855
$ curl  "http://localhost:8080/time?field=month"
5
$ curl  "http://localhost:8080/time?field=year"
2019
```

