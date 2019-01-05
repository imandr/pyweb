from .webob import Response
from .webob import Request as webob_request
from .webob.exc import HTTPTemporaryRedirect, HTTPException, HTTPFound
    
import os.path, os, stat, sys, traceback
from threading import RLock

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

def app_synchronized(method):
    def synchronized_method(self, *params, **args):
        with self._app_lock():
            return method(self, *params, **args)
    return synchronized_method


class WebPieHandler:

    Version = ""

    MIME_TYPES_BASE = {
        "gif":   "image/gif",
        "jpg":   "image/jpeg",
        "jpeg":   "image/jpeg",
        "js":   "text/javascript",
        "html":   "text/html",
        "txt":   "text/plain",
        "css":  "text/css"
    }

    def __init__(self, request, app, path = None):
        self.App = app
        self.Request = request
        self.Path = path
        self.BeingDestroyed = False
        self.AppURL = request.application_url
        #print "Handler created"

    def _app_lock(self):
        return self.App._app_lock()

    def initAtPath(self, path):
        # override me
        pass

    def myUri(self, down=None):
        #ret = "%s/%s" % (self.AppURI,self.MyPath)
        ret = self.MyPath
        if down:
            ret = "%s/%s" % (ret, down)
        return ret

    def find_object(self, path_to, obj, path_down):
        #print 'find_object(%s, %s)' % (path_to, path_down)
        path_down = path_down.lstrip('/')
        #print 'find_object(%s, %s)' % (path_to, path_down)
        if not path_down:
            # We've arrived, but method is empty
            return obj, 'index', ''
        parts = path_down.split('/', 1)
        next = parts[0]
        if len(parts) == 1:
            rest = ''
        else:
            rest = parts[1]
        # Hide private methods/attributes:
        assert not next.startswith('_')
        # Now we get the attribute; getattr(a, 'b') is equivalent
        # to a.b...
        next_obj = getattr(obj, next)
        if isinstance(next_obj, WebPieHandler):
            if path_to and path_to[-1] != '/':
                path_to += '/'
            path_to += next
            return self.find_object(path_to, next_obj, rest)
        else:
            return obj, next, rest

    def wsgi_call(self, environ, start_response):
        #print 'wsgi_call...'
        path_to = '/'
        path_down = environ.get('PATH_INFO', '')
        #print 'path:', path_down
        req = Request(environ)
        try:
            #print 'find_object..'
            obj, method, relpath = self.find_object(path_to, self, path_down)
        except AttributeError:
            resp = Response("Invalid path %s" % (path_down,), 
                            status = '500 Bad request')
        except AssertionError:
            resp = Response('Attempt to access private method',
                    status = '500 Bad request')
        else:
            m = getattr(obj, method)
            if not self._checkPermissions(m):
                resp = Response('Authorization required',
                    status = '403 Forbidden')
            else:
                dict = {}
                for k in req.GET.keys():
                    v = req.GET.getall(k)
                    if type(v) == type([]) and len(v) == 1:
                        v = v[0]
                    dict[k] = v
                try:
                    #print 'calling method: ',m
                    resp = m(req, relpath, **dict)
                    #print resp
                except HTTPException, val:
                    #print 'caught:', type(val), val
                    resp = val
                except HTTPResponseException, val:
                    #print 'caught:', type(val), val
                    resp = val
                except:
                    resp = self.App.applicationErrorResponse(
                        "Uncaught exception", sys.exc_info())
                if resp == None:
                    resp = req.getResponse()
        self.destroy()
        self._destroy()
        out = resp(environ, start_response)
        return out

    def hello(self, req, relpath):
        resp = Response("Hello")
        return resp
       
    def env(self, req, relpath):
        return Response(app_iter = [
            "%s = %s\n" % (k, repr(v)) for k, v in sorted(req.environ.items())
        ], content_type="text/plain")

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

    def static(self, req, rel_path, **args):
        while ".." in rel_path:
            rel_path = rel_path.replace("..",".")
        home = self.App.ScriptHome
        path = os.path.join(home, "static", rel_path)
        try:
            st_mode = os.stat(path).st_mode
            if not stat.S_ISREG(st_mode):
                #print "not a regular file"
                raise ValueError("Not a regular file")
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
            
        return Response(app_iter = read_iter(open(path, "rb")),
            content_type = mime_type)

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
    
class WebPieApp:

    Version = "Undefined"

    def __init__(self, root_class):
        self.RootClass = root_class
        self.JEnv = None
        self._AppLock = RLock()

    def _app_lock(self):
        return self._AppLock
    
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

    def __call__(self, environ, start_response):
        #print 'app call ...'
        path_to = '/'
        path_down = environ.get('PATH_INFO', '')
        #print 'path:', path_down
        req = Request(environ)
        self.ScriptName = environ.get('SCRIPT_NAME','')
        self.Script = environ.get('SCRIPT_FILENAME', 
                    os.environ.get('UWSGI_SCRIPT_FILENAME'))
        self.ScriptHome = os.path.dirname(self.Script or sys.argv[0]) or "."
        root = self.RootClass(req, self, "/")
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
        
if __name__ == '__main__':
    from HTTPServer import HTTPServer
    
    class MyApp(WebPieApp):
        pass
        
    class MyHandler(WebPieHandler):
        pass
            
    app = MyApp(MyHandler)
    hs = HTTPServer(8001, "*", app)
    hs.start()
    hs.join()
