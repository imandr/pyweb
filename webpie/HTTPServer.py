import fnmatch, traceback, sys, select
from socket import *
from pythreader import PyThread, synchronized

class InputStream:
    
    def __init__(self, lst):
        self.Data = lst[:]
        
    def read(self, n = -1):
        out = ''
        while self.Data and (n < 0 or len(out) < n):
            w = self.Data[0]
            if n > 0:
                rest = n - len(out)
                if len(w) > rest:
                    self.Data[0] = w[rest:]
                    w = w[:rest]
                else:
                    self.Data = self.Data[1:]
            out += w
        return out

class HTTPConnection(PyThread):

    MAXMSG = 100000

    def __init__(self, server, csock, caddr):
        PyThread.__init__(self)
        self.Server = server
        self.CAddr = caddr
        self.CSock = csock
        self.ReadClosed = False
        self.Request = None
        self.RequestBuffer = ''
        self.Body = []
        self.URL = None
        self.Headers = []
        self.HeadersDict = {}
        self.URL = None
        self.RequestMethod = None
        self.RequestReceived = False
        self.QueryString = ''
        self.OutBuffer = []
        self.OutputEnabled = False

    def requestReceived(self):
        #self.debug("requestReceived:[%s]" % (self.RequestBuffer,))
        # parse the request
        lines = self.RequestBuffer.split('\n')
        lines = [l.strip() for l in lines if l.strip()]
        if not lines:
            self.shutdown()
            return
        self.Request = lines[0].strip()
        words = self.Request.split()
        #self.debug("Request: %s" % (words,))
        if len(words) != 3:
            self.shutdown()
            return
        self.RequestMethod = words[0].upper()
        self.RequestProtocol = words[2]
        self.URL = words[1]
        uwords = self.URL.split('?',1)
        self.PathInfo = uwords[0]
        if not self.Server.urlMatch(self.PathInfo):
            self.shutdown()
            return
        if len(uwords) > 1: self.QueryString = uwords[1]
        #ignore HTTP protocol
        for h in lines[1:]:
            words = h.split(':',1)
            name = words[0].strip()
            value = ''
            if len(words) > 1:
                value = words[1].strip()
            if name:
                self.Headers.append((name, value))
                self.HeadersDict[name] = value
        self.processRequest()
        
    def getHeader(self, header, default = None):
        # case-insensitive version of dictionary lookup
        h = header.lower()
        for k, v in self.HeadersDict.items():
            if k.lower() == h:
                return v
        return default
        
    def addToRequest(self, data):
        #self.debug("Add to request(%s)" % (data,))
        self.RequestBuffer += data
        inx = self.RequestBuffer.find('\n\n')
        if inx < 0: inx = self.RequestBuffer.find('\r\n\r\n')
        if inx >= 0:
            #self.debug("End of headers found")
            rest = self.RequestBuffer[inx+2:].lstrip()
            self.RequestBuffer = self.RequestBuffer[:inx]
            self.requestReceived()
            if rest:    self.addToBody(rest)
            
    def addToBody(self, data):
        self.Body.append(data)

    def parseQuery(self, query):
        out = {}
        for w in query.split("&"):
            if w:
                words = w.split("=", 1)
                k = words[0]
                if k:
                    v = None
                    if len(words) > 1:  v = words[1]
                    if out.has_key(k):
                        old = out[k]
                        if type(old) != type([]):
                            old = [old]
                            out[k] = old
                        out[k].append(v)
                    else:
                        out[k] = v
        return out
                
    def processRequest(self):        
        #self.debug("processRequest()")
        env = dict(
            REQUEST_METHOD = self.RequestMethod.upper(),
            PATH_INFO = self.PathInfo,
            SCRIPT_NAME = "",
            SERVER_PROTOCOL = self.RequestProtocol,
            QUERY_STRING = self.QueryString
        )
        
        env["wsgi.input"] = InputStream(self.Body)
        env["wsgi.url_scheme"] = "http"
        env["query_dict"] = self.parseQuery(self.QueryString)
        
        for h, v in self.HeadersDict.items():
            h = h.lower()
            if h == "content-type": env["CONTENT_TYPE"] = v
            elif h == "host":
                words = v.split(":",1)
                words.append("")    # default port number
                env["HTTP_HOST"] = words[0]
                env["SERVER_NAME"] = words[0]
                env["SERVER_PORT"] = words[1]
            elif h == "content-length": 
                env["CONTENT_LENGTH"] = v
            else:
                env["HTTP_%s" % (h.upper().replace("-","_"),)] = v

        try:    
                #self.debug("call wsgi_app")
                output = self.Server.wsgi_app(env, self.start_response)    
                self.OutBuffer += output
                #self.debug("wsgi_app done")
                
        except:
                #self.debug("Error: %s %s" % sys.exc_info()[:2])
                self.start_response("500 Error", 
                                [("Content-Type","text/plain")])
                self.OutBuffer += [traceback.format_exc()]
        self.OutputEnabled = True
        #self.debug("registering for writing: %s" % (self.CSock.fileno(),))    

    def start_response(self, status, headers):
        #self.debug("start_response()")
        self.OutBuffer.append("HTTP/1.1 " + status + "\n")
        for h,v in headers:
            self.OutBuffer.append("%s: %s\n" % (h, v))
        self.OutBuffer.append("\n")
        
    def doClientRead(self):
        if self.ReadClosed:
            return

        try:    data = self.CSock.recv(self.MAXMSG)
        except: data = ''
    
        self.ReadClosed = (not data)

        if not self.Request:
            self.addToRequest(data)
        else:
            self.addToBody(data)

        if self.ReadClosed and not self.Request:
            self.shutdown()
                    
    def doRead(self, fd, sel):
        if fd == self.CSock.fileno():
            self.doClientRead(sel)
            
    def doWrite(self):
        if self.OutBuffer:
            line = self.OutBuffer[0]
            try:    sent = self.CSock.send(line)
            except: sent = 0
            if not sent:
                #self.debug("write socket closed")
                self.shutdown()
                return
            else:
                line = line[sent:]
                if line:
                    self.OutBuffer[0] = line
                else:
                    self.OutBuffer = self.OutBuffer[1:]
        
    def shutdown(self):
            #self.debug("shutdown")
            if self.CSock != None:
                #self.debug("closing socket")
                self.CSock.close()
                self.CSock = None
            if self.Server is not None:
                self.Server.connectionClosed(self)
                self.Server = None
            
    def run(self):
        while self.CSock is not None:       # shutdown() will set it to None
            rlist = [] if self.ReadClosed else [self.CSock]
            wlist = [self.CSock] if self.OutputEnabled else []
            rlist, wlist, exlist = select.select(rlist, wlist, [], 10.0)
            if self.CSock in rlist:
                self.doClientRead()
            if self.CSock in wlist:
                self.doWrite()
            if self.OutputEnabled and not self.OutBuffer:
                self.shutdown()     # noting else to send
    

class HTTPServer(PyThread):

    def __init__(self, port, app, url_pattern="*", max_connections = 100, enabled = True):
        PyThread.__init__(self)
        #self.debug("Server started")
        self.Port = port
        self.WSGIApp = app
        self.Match = url_pattern
        self.Enabled = False
        self.Connections = []
        self.MaxConnections = max_connections
        if enabled:
            self.enableServer()
        

    def urlMatch(self, path):
        return fnmatch.fnmatch(path, self.Match)

    def wsgi_app(self, env, start_response):
        return self.WSGIApp(env, start_response)
        
    @synchronized
    def enableServer(self, backlog = 5):
        self.Enabled = True
                
    @synchronized
    def disableServer(self):
        self.Enabled = False

    @synchronized
    def connectionClosed(self, conn):
        if conn in self.Connections:
            self.Connections.remove(conn)
            
    @synchronized
    def connectionCount(self):
        return len(self.Connections)    
            
    def run(self):
        self.Sock = socket(AF_INET, SOCK_STREAM)
        self.Sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self.Sock.bind(('', self.Port))
        self.Sock.listen(10)
        while True:
            rlist, _, _  = select.select([self.Sock], [], [], 1)
            if self.Enabled and self.connectionCount() < self.MaxConnections:
                csock, caddr = self.Sock.accept()
                conn = HTTPConnection(self, csock, caddr)
                self.Connections.append(conn)
                conn.start()
                
                
def run_server(port, app, url_pattern="*"):
    srv = HTTPServer(port, app, url_pattern=url_pattern)
    srv.start()
    srv.join()
    

if __name__ == '__main__':

    def app(env, start_response):
        start_response("200 OK", [("Content-Type","text/plain")])
        return (
            "%s = %s\n" % (k,v) for k, v in env.items()
            )

    run_server(8000, app)
