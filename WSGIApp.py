from .webob import Response
from .webob import Request as webob_request
import webob, traceback, sys
from .webob.exc import HTTPTemporaryRedirect, HTTPException, HTTPFound
import os.path, os, stat
from pythreader import Primitive

class Request(webob_request):
    def __init__(self, *agrs, **kv):
        webob.Request.__init__(self, *agrs, **kv)
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



    
class PyWebHandler:

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
        self.MyPath = path
        self.BeingDestroyed = False
        #print "Handler created"

    def setPath(self, path):
        self.MyPath = path

    def myUri(self, down=None):
        #ret = "%s/%s" % (self.AppURI,self.MyPath)
        ret = self.MyPath
        if down:
            ret = "%s/%s" % (ret, down)
        return ret

    def static(self, req, rel_path, **args):
        rel_path = rel_path.replace("..",".")
        home = self.App.ScriptHome
        path = os.path.join(home, "static", rel_path)
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
            
        return Response(app_iter = read_iter(open(path, "rb")),
            content_type = mime_type)

    def _destroy(self):
        self.App = None
        if self.BeingDestroyed: return      # avoid infinite loops
        self.BeingDestroyed = True
        for k in self.__dict__:
            o = self.__dict__[k]
            if isinstance(o, WSGIHandler):
                try:    o.destroy()
                except: pass
                o._destroy()
        self.BeingDestroyed = False
        
    def hello(self, req, relpath):
        resp = Response("Hello")
        return resp
       
    def destroy(self):
        # override me
        pass

    def initAtPath(self, path):
        # override me
        pass

    def render_to_string(self, temp, **args):
        return self.App.render_to_string(temp, **args)

    def render_to_iterator(self, temp, **args):
        return self.App.render_to_iterator(temp, **args)

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
    
_UseJinja2 = True

try:
    import jinja2
except:
    _UseJinja2 = False

class J2Env:
    def __init__(self, homedir):
        if _UseJinja2:
            from jinja2 import Environment, FileSystemLoader
            tempdirs = [homedir, os.path.join(homedir, 'templates']
            self.JEnv = Environment(
                loader=FileSystemLoader(tempdirs)
                )
            self.JGlobals = {}

    def addFilters(self, filters):
        for n, f in filters.items():
            self.JEnv.filters[n] = f
            
    def addGlobals(self, gbl):
        self.JGlobals.update(gbl)
        
    def render_to_string(self, temp, **kv):
        t = self.JEnv.get_template(temp)
        return t.render(self.addEnvironment(kv))

    def render_to_iterator(self, temp, **kv):
        t = self.JEnv.get_template(temp)
        return t.generate(self.addEnvironment(kv))
        
class PyWebApp(Primitive):

    Version = "Undefined"

    def __init__(self, root_class):
        Primitive.__init__(self)
        self.RootClass = root_class
        self.Initialized = False
        
    @synchronized
    def initOnce(self, request):
        if not self.Initialized:
            self.Script = request.environ.get('SCRIPT_FILENAME', 
                os.environ.get('UWSGI_SCRIPT_FILENAME'))
            self.ScriptHome = os.path.dirname(self.Script or sys.argv[0]) or "."
            if _UseJinja2:
                self.JEnv = J2Env(self.ScriptHome)
            self.Initialized = True
        
    def setJinjaFilters(self, filters):
        self.JEnv.addFilters(filters)

    def setJinjaGlobals(self, globals):
        self.JEnv.addGlobals(globals)

    def destroy(self):
        # override me
        pass

    def find_object(self, path_to, obj, path_down):
        #print 'find_object(%s, %s)' % (path_to, path_down)
        path_down = path_down.lstrip('/')
        #print 'find_object(%s, %s)' % (path_to, path_down)
        obj.setPath(path_to)
        obj.initAtPath(path_to)
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
        if isinstance(next_obj, WSGIHandler):
            if path_to and path_to[-1] != '/':
                path_to += '/'
            path_to += next
            return self.find_object(path_to, next_obj, rest)
        else:
            return obj, next, rest

    def init(self, root):
        # override me
        # called from wsgi call right after the root handler is created,
        # at this point, self.Request.environ is ready to be used 
        pass
  
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

    def applicationErrorResponse(self, headline, exc_info):
        typ, val, tb = exc_info
        exc_text = traceback.format_exception(typ, val, tb)
        exc_text = ''.join(exc_text)
        text = """<html><body><h2>Application error</h2>
            <h3>%s</h3>
            <pre>%s</pre>
            </body>
            </html>""" % (headline, exc_text)
        print exc_text
        return Response(text, status = '500 Application Error')
    
    
    def wsgi_call(self, environ, start_response):
        req = Request(environ)
        self.initOnce(req)
        #print 'wsgi_call...'
        path_to = '/'
        path_down = environ.get('PATH_INFO', '')
        #print 'path:', path_down
        self.ScriptName = environ.get('SCRIPT_NAME','')
        root = self.RootClass(req, self)
        #print 'root created'
        #print 'initialized'
        try:
            #print 'find_object..'
            obj, method, relpath = self.find_object(path_to, root, path_down)
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
                for k in req.str_GET.keys():
                    v = req.str_GET.getall(k)
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
                    resp = self.applicationErrorResponse(
                        "Uncaught exception", sys.exc_info())
                if resp == None:
                    resp = req.getResponse()
        out = resp(environ, start_response)
        root._destroy()
        self.destroy()
        #print out
        return out
        
    def __call__(self, environ, start_response):
        return self.wsgi_call(environ, start_response)
            
    def render_to_string(self, temp, **kv):
        params = {
            "GLOBAL_AppVersion":    self.Version,
            "GLOBAL_AppObject":     self
            }
        params.update(kv)
        return self.JEnv.render_to_string(temp, **params)

    def render_to_iterator(self, temp, **kv):
        params = {
            "GLOBAL_AppVersion":    self.Version,
            "GLOBAL_AppObject":     self
            }
        params.update(kv)
        return self.JEnv.render_to_iterator(temp, **params)
        
def createApplication(appclass, handlerclass, *params, **args):
    return appclass(handlerclass, *params, **args)
    


        
if __name__ == '__main__':
    from .HTTPServer import HTTPServer
    
    class MyApp(PyWebApp):
        pass
        
    class MyHandler(PyWebHandler):
    
        def env(self, request, relpath, **args):
            resp_lines = (
                "%s = %s\n" % (k, v) for k, v in request.environ.items()
                )
            return Response(app_iter = resp_lines, content_type="text/plain")
            
    app = createApplication(MyApp, MyHandler)
    hs = HTTPServer(8001, "*", app)
    hs.start()
    hs.join()
