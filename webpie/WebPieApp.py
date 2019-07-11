from .webob import Response
from .webob import Request as webob_request
from .webob.exc import HTTPTemporaryRedirect, HTTPException, HTTPFound, HTTPForbidden, HTTPNotFound
    
import os.path, os, stat, sys, traceback, fnmatch
from threading import RLock

PY2 = sys.version_info[0] == 2
PY3 = sys.version_info[0] == 3

try:
    from collections.abc import Iterable    # Python3
except ImportError:
    from collections import Iterable

_WebMethodSignature = "__WebPie:webmethod__"

#
# Decorators
#
 
def webmethod(permissions=None):
    #
    # Usage:
    #
    # class Handler(WebPieHandler):
    #   ...
    #   @webmethod()            # <-- important: parenthesis required !
    #   def hello(self, req, relpath, **args):
    #       ...
    #
    #   @webmethod(permissions=["admin"])
    #   def method(self, req, relpath, **args):
    #       ...
    #
    def decorator(method):
        def decorated(handler, request, relpath, *params, **args):
            #if isinstance(permissions, str):
            #    permissions = [permissions]
            if permissions is not None:
                try:    roles = handler._roles(request, relpath)
                except:
                    return HTTPForbidden("Can not authorize client")
                if isinstance(roles, str):
                    roles = [roles]
                for r in roles:
                    if r in permissions:
                        break
                else:
                    return HTTPForbidden()
            return method(handler, request, relpath, *params, **args)
        decorated.__doc__ = _WebMethodSignature
        return decorated
    return decorator

def app_synchronized(method):
    def synchronized_method(self, *params, **args):
        with self._app_lock():
            return method(self, *params, **args)
    return synchronized_method

atomic = app_synchronized

class Request(webob_request):
    def __init__(self, *agrs, **kv):
        webob_request.__init__(self, *agrs, **kv)
        self.args = self.environ['QUERY_STRING']
        self._response = Response()
        
    def write(self, txt):
        self._response.write(txt)
        
    def getResponse(self):
        return self._response
        
    def set_response_content_type(self, t):
        self._response.content_type = t
        
    def get_response_content_type(self):
        return self._response.content_type
        
    def del_response_content_type(self):
        pass
        
    response_content_type = property(get_response_content_type, 
        set_response_content_type,
        del_response_content_type, 
        "Response content type")

class HTTPResponseException(Exception):
    def __init__(self, response):
        self.value = response


def makeResponse(resp):
    #
    # acceptable responses:
    #
    # Response
    # text              -- ala Flask
    # (text, status)            
    # (text, "content_type")            
    # (text, {headers})            
    # (text, status, "content_type")
    # (text, status, {headers})
    #
    
    if isinstance(resp, Response):
        return resp
    
    body_or_iter = None
    content_type = None
    status = None
    extra = None
    if isinstance(resp, tuple) and len(resp) == 2:
        body_or_iter, extra = resp
    elif isinstance(resp, tuple) and len(resp) == 3:
        body_or_iter, status, extra = resp
    elif PY2 and isinstance(resp, (str, bytes, unicode)):
        body_or_iter = resp
    elif PY3 and isinstance(resp, (str, bytes)):
        body_or_iter = resp
    elif isinstance(resp, Iterable):
        body_or_iter = resp
    else:
        raise ValueError("Handler method returned uninterpretable value: " + repr(resp))
        
    response = Response()
    
    if isinstance(body_or_iter, str):
        if sys.version_info >= (3,):
            response.text = body_or_iter
        else:
            response.text = unicode(body_or_iter, "utf-8")
    elif isinstance(body_or_iter, bytes):
        response.body = body_or_iter
    elif isinstance(body_or_iter, Iterable):
        response.app_iter = body_or_iter
    else:
        raise ValueError("Unknown type for response body: " + str(type(body_or_iter)))

    #print "makeResponse: extra: %s %s is str:%s" % (type(extra), extra, isinstance(extra, str))
    
    if status is not None:
        response.status = status
     
    if extra is not None:
        if isinstance(extra, dict):
            response.headers = extra
        elif isinstance(extra, str):
            response.content_type = extra
        elif isinstance(extra, int):
            #print "makeResponse: setting status to %s" % (extra,)
            response.status = extra
        else:
            raise ValueError("Unknown type for headers: " + repr(extra))
#print response
    
    return response


class WPHandler:

    Version = ""

    _Methods = None
    
    def __init__(self, request, app):
        self.App = app
        self.BeingDestroyed = False
        try:    self.AppURL = request.application_url
        except: self.AppURL = None
        self.RouteMap = []
        self.Request = request

    def addHandler(self, pattern, handler, status=200, content_type="text/plain"):
        if isinstance(handler, WPHandler):
            self.RouteMap.append((pattern, handler))
        elif callable(handler):
            self.addHandler(pattern, WPLambdaHandler(self.Request, self.App, handler))
        elif isinstance(handler, (str, unicode)):
            self.addHandler(pattern, WPResponder(self.Request, self.App, handler, status, content_type))
            
    def _app_lock(self):
        return self.App._app_lock()

    def initAtPath(self, path):
        # override me
        pass

        
    def wsgi_call(self, environ, start_response):
        path_to = '/'
        path = environ.get('PATH_INFO', '')
        path_down = path.split("/")
        try:
            environ["query_dict"] = self.parseQuery(environ.get("QUERY_STRING", ""))
            request = Request(environ)
            response = self.walk_down(request, path_to, path_down)    
        except HTTPFound as val:    
            # redirect
            response = val
        except HTTPException as val:
            #print 'caught:', type(val), val
            response = val
        except HTTPResponseException as val:
            #print 'caught:', type(val), val
            response = val
        except:
            response = self.App.applicationErrorResponse(
                "Uncaught exception", sys.exc_info())
        
        out = response(environ, start_response)
        self.destroy()
        self._destroy()
        return out
        
    def parseQuery(self, query):
        out = {}
        for w in (query or "").split("&"):
            if w:
                words = w.split("=", 1)
                k = words[0]
                if k:
                    v = None
                    if len(words) > 1:  v = words[1]
                    if k in out:
                        old = out[k]
                        if type(old) != type([]):
                            old = [old]
                            out[k] = old
                        out[k].append(v)
                    else:
                        out[k] = v
        return out
        
    def walk_down(self, request, path_to, path_down):
        self.Path = path_to
        while path_down and not path_down[0]:
            path_down = path_down[1:]

        method = None
        response = None
        if not path_down:
            # if empty path
            if hasattr(self, "index"):                  # try index
                response = self.redirect("index")
            elif callable(self):                        # or __call__
                response = self(request, "", **request.environ["query_dict"])
        else:
            item_name = path_down[0]
            if hasattr(self, item_name):
                path_down = path_down[1:]
                item = getattr(self, item_name)
                if isinstance(item, WPHandler):
                    if path_to[-1] != '/':  path_to += '/'
                    path_to += item_name
                    response = item.walk_down(request, path_to, path_down)
                elif callable(item):
                    allowed = False
                    if self.App._Strict:
                        allowed = (
                                (self._Methods is not None 
                                        and item_name in self._Methods)
                            or
                                (hasattr(item, "__doc__") 
                                        and item.__doc__ == _WebMethodSignature)
                            )
                    else:
                        allowed = self._Methods is None or method_name in self._Methods
                    if allowed:
                        relpath = "/".join(path_down)
                        response = item(request, relpath, **request.environ["query_dict"])
                    else:
                        return HTTPForbidden(request.path_info)
            else:
                relpath = "/".join(path_down)
                for pattern, handler in self.RouteMap:
                    if fnmatch.fnmatch(pattern, relpath):
                        if path_to[-1] != '/':  path_to += '/'
                        path_to += item_name
                        response = handler.walk_down(request, path_to, path_down[1:])
                    
        if response is None and callable(self):
            relpath = "/".join(path_down)
            response = self(request, relpath, **request.environ["query_dict"])
                    
        if response is None:
            return HTTPNotFound("Invalid path %s" % (request.path_info,))
        
        try:    
            response = makeResponse(response)
        except ValueError as e:
            response = self.App.applicationErrorResponse(str(e), sys.exc_info())
    
        return response
                

    def hello(self, req, relpath):
        resp = Response("Hello")
        return resp
       
    def env(self, req, relpath):
        return (
            "%s = %s\n" % (k, repr(v)) for k, v in sorted(req.environ.items())
        ), "text/plain"

    def _checkPermissions(self, x):
        #self.apacheLog("doc: %s" % (x.__doc__,))
        try:    docstr = x.__doc__
        except: docstr = None
        if docstr and docstr[:10] == '__roles__:':
            roles = [x.strip() for x in docstr[10:].strip().split(',')]
            #self.apacheLog("roles: %s" % (roles,))
            return self.checkRoles(roles)
        return True
        
    def checkRoles(self, roles):
        # override me
        return True

    def _destroy(self):
        self.App = None
        if self.BeingDestroyed: return      # avoid infinite loops
        self.BeingDestroyed = True
        for k in self.__dict__:
            o = self.__dict__[k]
            if isinstance(o, WebPieHandler):
                try:    o.destroy()
                except: pass
                o._destroy()
        self.BeingDestroyed = False
        
    def destroy(self):
        # override me
        pass

    def initAtPath(self, path):
        # override me
        pass

    def addEnvironment(self, d):
        params = {  
            'APP_URL':  self.AppURL,
            'MY_PATH':  self.Path,
            "GLOBAL_AppTopPath":    self.scriptUri(),
            "GLOBAL_AppDirPath":    self.uriDir(),
            "GLOBAL_ImagesPath":    self.uriDir()+"/images",
            "GLOBAL_AppVersion":    self.Version,
            "GLOBAL_AppObject":     self,
            }
        params = self.App.addEnvironment(params)
        params.update(d)
        return params

    def render_to_string(self, temp, **args):
        params = self.addEnvironment(args)
        return self.App.render_to_string(temp, **params)

    def render_to_iterator(self, temp, **args):
        params = self.addEnvironment(args)
        #print 'render_to_iterator:', params
        return self.App.render_to_iterator(temp, **params)

    def render_to_response(self, temp, **more_args):
        return Response(self.render_to_string(temp, **more_args))

    def mergeLines(self, iter, n=50):
        buf = []
        for l in iter:
            if len(buf) >= n:
                yield ''.join(buf)
                buf = []
            buf.append(l)
        if buf:
            yield ''.join(buf)

    def render_to_response_iterator(self, temp, _merge_lines=0,
                    **more_args):
        it = self.render_to_iterator(temp, **more_args)
        #print it
        if _merge_lines > 1:
            merged = self.mergeLines(it, _merge_lines)
        else:
            merged = it
        return Response(app_iter = merged)

    def redirect(self, location):
        #print 'redirect to: ', location
        #raise HTTPTemporaryRedirect(location=location)
        raise HTTPFound(location=location)
        
    def getSessionData(self):
        return self.App.getSessionData()
        
        
    def scriptUri(self, ignored=None):
        return self.Request.environ.get('SCRIPT_NAME',
                os.environ.get('SCRIPT_NAME', '')
        )
        
    def uriDir(self, ignored=None):
        return os.path.dirname(self.scriptUri())
        
    def renderTemplate(self, ignored, template, _dict = {}, **args):
        # backward compatibility method
        params = {}
        params.update(_dict)
        params.update(args)
        raise HTTPException("200 OK", self.render_to_response(template, **params))

    def env(self, req, relpath, **args):
        lines = ["WSGI environment\n----------------------\n"]
        for k in sorted(req.environ.keys()):
            lines.append("%s = %s\n" % (k, req.environ[k]))
        return Response(app_iter = lines, content_type = "text/plain")
    
    @property
    def session(self):
        return self.Request.environ["webpie.session"]

class WPLambdaHandler(WPHandler):
    
    def __init__(self, request, app, callable):
        WPHandler.__init__(self, request, app)
        self.F = callable
        
    def __call__(self, req, relpath, **args):
        return self.F(req, relpath, **args)
        
class WPResponder(WPHandler):
    
    def __init__(self, request, app, body, status=200, content_type="text/plain"):
        WPHandler.__init__(self, request, app)
        self.Response = makeResponse((body, status, content_type))
        #print "Responder: status=%s" % (status,)
        #print self.Response, self.Response.status
        
    def __call__(self, req, relpath, **args):
        return self.Response
        
class WebPieHandler(WPHandler):     # for compatibility. Migrate to WPHandler
    
    def __init__(self, request, app, path = None):
        WPHandler.__init__(self, request, app)
        self.Path = path
        
class WPApp:

    Version = "Undefined"

    def __init__(self, root_class, strict=False, 
            static_path="/static", static_location="static", enable_static=True,
            disable_robots=True):
        assert issubclass(root_class, WPHandler)
        self.RootClass = root_class
        self.JEnv = None
        self._AppLock = RLock()
        self._Strict = strict
        self.ScriptHome = None
        self.StaticPath = static_path
        self.StaticLocation = static_location
        self.StaticEnabled = enable_static and static_location
        self.Initialized = False
        self.DisableRobots = disable_robots

    def _app_lock(self):
        return self._AppLock
        
    def __enter__(self):
        return self._AppLock.__enter__()
        
    def __exit__(self, *params):
        return self._AppLock.__exit(*params)
    
    # override
    @app_synchronized
    def acceptIncomingTransfer(self, method, uri, headers):
        return True
            
    @app_synchronized
    def initJinjaEnvironment(self, tempdirs = [], filters = {}, globals = {}):
        # to be called by subclass
        #print "initJinja2(%s)" % (tempdirs,)
        from jinja2 import Environment, FileSystemLoader
        if not isinstance(tempdirs, list):
            tempdirs = [tempdirs]
        self.JEnv = Environment(
            loader=FileSystemLoader(tempdirs)
            )
        for n, f in filters.items():
            self.JEnv.filters[n] = f
        self.JGlobals = {}
        self.JGlobals.update(globals)
                
    @app_synchronized
    def setJinjaFilters(self, filters):
            for n, f in filters.items():
                self.JEnv.filters[n] = f

    @app_synchronized
    def setJinjaGlobals(self, globals):
            self.JGlobals = {}
            self.JGlobals.update(globals)
        
    def applicationErrorResponse(self, headline, exc_info):
        typ, val, tb = exc_info
        exc_text = traceback.format_exception(typ, val, tb)
        exc_text = ''.join(exc_text)
        text = """<html><body><h2>Application error</h2>
            <h3>%s</h3>
            <pre>%s</pre>
            </body>
            </html>""" % (headline, exc_text)
        #print exc_text
        return Response(text, status = '500 Application Error')

    MIME_TYPES_BASE = {
        "gif":   "image/gif",
        "jpg":   "image/jpeg",
        "jpeg":   "image/jpeg",
        "js":   "text/javascript",
        "html":   "text/html",
        "txt":   "text/plain",
        "css":  "text/css"
    }

    def static(self, relpath):
        while ".." in relpath:
            relpath = relpath.replace("..",".")
        home = self.StaticLocation
        path = os.path.join(home, relpath)
        #print "static: path=", path
        try:
            st_mode = os.stat(path).st_mode
            if not stat.S_ISREG(st_mode):
                #print "not a regular file"
                raise ValueError("Not regular file")
        except:
            #raise
            return Response("Not found", status=404)

        ext = path.rsplit('.',1)[-1]
        mime_type = self.MIME_TYPES_BASE.get(ext, "text/html")

        def read_iter(f):
            while True:
                data = f.read(100000)
                if not data:    break
                yield data
        #print "returning response..."
        return Response(app_iter = read_iter(open(path, "rb")),
            content_type = mime_type)

    def __call__(self, environ, start_response):
        #print 'app call ...'
        path_to = '/'
        path_down = environ.get('PATH_INFO', '')
        #print 'path:', path_down
        req = Request(environ)
        if not self.Initialized:
            self.ScriptName = environ.get('SCRIPT_NAME','')
            self.Script = environ.get('SCRIPT_FILENAME', 
                        os.environ.get('UWSGI_SCRIPT_FILENAME'))
            self.ScriptHome = os.path.dirname(self.Script or sys.argv[0]) or "."
            if self.StaticEnabled:
                if not self.StaticLocation[0] in ('.', '/'):
                    self.StaticLocation = self.ScriptHome + "/" + self.StaticLocation
                    #print "static location:", self.StaticLocation
            self.Initialized = True
            
        if self.StaticEnabled and path_down.startswith(self.StaticPath+"/"):
            path = path_down[len(self.StaticPath)+1:]
            resp = self.static(path)
        elif self.DisableRobots and path_down.endswith("/robots.txt"):
            resp = Response("User-agent: *\nDisallow: /\n", content_type = "text/plain")
        else:
            if issubclass(self.RootClass, WebPieHandler):
                try:    
                    root = self.RootClass(req, self)
                except:
                    raise
                    root = self.RootClass(req, self, "/")
            else:
                root = RootClass(self)
            try:
                return root.wsgi_call(environ, start_response)
            except:
                resp = self.applicationErrorResponse(
                    "Uncaught exception", sys.exc_info())
        return resp(environ, start_response)
        
    def JinjaGlobals(self):
        # override me
        return {}

    def addEnvironment(self, d):
        params = {}
        params.update(self.JGlobals)
        params.update(self.JinjaGlobals())
        params.update(d)
        return params
        
    def render_to_string(self, temp, **kv):
        t = self.JEnv.get_template(temp)
        return t.render(self.addEnvironment(kv))

    def render_to_iterator(self, temp, **kv):
        t = self.JEnv.get_template(temp)
        return t.generate(self.addEnvironment(kv))

    def run_server(self, port, **args):
        from .HTTPServer import HTTPServer
        srv = HTTPServer(port, self, **args)
        srv.start()
        srv.join()

WebPieApp = WPApp
        
if __name__ == '__main__':
    from HTTPServer import HTTPServer
    
    class MyApp(WebPieApp):
        pass
        
    class MyHandler(WebPieHandler):
        pass
            
    MyApp(MyHandler).run_server(8080)
