import fnmatch, traceback, sys, select, time
from socket import *
from pythreader import PyThread, synchronized, Task, TaskQueue

        
class BodyFile(object):
    
    def __init__(self, buf, sock, length):
        self.Buffer = buf
        self.Sock = sock
        self.Remaining = length
        
    def get_chunk(self, n):
        if self.Buffer:
            chunk = self.Buffer[0]
            if len(chunk) > n:
                out = chunk[:n]
                self.Buffer[0] = chunk[n:]
            else:
                out = chunk
                self.Buffer = self.Buffer[1:]
        elif self.Sock is not None:
            out = self.Sock.recv(n)
            if not out: self.Sock = None
        return out
        
    MAXMSG = 100000
    
    def read(self, N = None):
        #print ("read({})".format(N))
        #print ("Buffer:", self.Buffer)
        if N is None:   N = self.Remaining
        out = []
        n = 0
        eof = False
        while not eof and (N is None or n < N):
            ntoread = self.MAXMSG if N is None else N - n
            chunk = self.get_chunk(ntoread)
            if not chunk:
                eof = True
            else:
                n += len(chunk)
                out.append(chunk)
        out = b''.join(out)
        if self.Remaining is not None:
            self.Remaining -= len(out)
        #print ("returning:[{}]".format(out))
        return out
            
            
class HTTPConnection(Task):

    MAXMSG = 100000

    def __init__(self, server, csock, caddr):
        Task.__init__(self)
        self.Server = server
        self.CAddr = caddr
        self.CSock = csock
        self.ReadClosed = False
        self.Request = None
        self.RequestBuffer = ""
        self.Body = []
        self.Headers = []
        self.HeadersDict = {}
        self.URL = None
        self.RequestMethod = None
        self.RequestReceived = False
        self.QueryString = ""
        self.OutBuffer = []
        self.OutputEnabled = False
        self.BodyLength = None
        self.BytesSent = 0
        self.ResponseStatus = None

    def requestReceived(self):
        #print("requestReceived:[%s]" % (self.RequestBuffer,))
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
        
    def getHeader(self, header, default = None):
        # case-insensitive version of dictionary lookup
        h = header.lower()
        for k, v in self.HeadersDict.items():
            if k.lower() == h:
                return v
        return default
        
    def addToRequest(self, data):
        #print("Add to request:", data)
        self.RequestBuffer += data
        inx_nn = self.RequestBuffer.find('\n\n')
        inx_rnrn = self.RequestBuffer.find('\r\n\r\n')
        if inx_nn < 0:
            inx = inx_rnrn
            n = 4
        elif inx_rnrn < 0:
            inx = inx_nn
            n = 2
        elif inx_nn < inx_rnrn:
            inx = inx_nn
            n = 2
        else:
            inx = inx_rnrn
            n = 4
        #print ("addToRequest: inx={}, n={}".format(inx, n))
        if inx >= 0:
            rest = self.RequestBuffer[inx+n:]
            self.RequestBuffer = self.RequestBuffer[:inx]
            self.requestReceived()
            #print("rest:[{}]".format(rest))
            if rest:    
                self.addToBody(rest)
            self.processRequest()
            
    def addToBody(self, data):
        if isinstance(data, str):   data = bytes(data, "utf-8")
        #print ("addToBody:", data)
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
                    if k in out:
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
        
        if self.HeadersDict.get("Expect") == "100-continue":
            if True: #self.Server.acceptIncomingTransfer(self.RequestMethod, self.URL, self.HeadersDict):
                self.CSock.send(b'HTTP/1.1 100 Continue\n\n')
            else:
                self.start_response("403 Object is rejected", [])
                self.OutputEnabled = True
                return []
                
        env["wsgi.url_scheme"] = "http"
        env["query_dict"] = self.parseQuery(self.QueryString)
        
        #print ("processRequest: env={}".format(env))
        
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
                env["CONTENT_LENGTH"] = self.BodyLength = int(v)
            else:
                env["HTTP_%s" % (h.upper().replace("-","_"),)] = v

        env["wsgi.input"] = BodyFile(self.Body, self.CSock, self.BodyLength)

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
        #print("start_response({}, {})".format(status, headers))
        self.ResponseStatus = status.split()[0]
        self.OutBuffer.append("HTTP/1.1 " + status + "\n")
        for h,v in headers:
            self.OutBuffer.append("%s: %s\n" % (h, v))
        self.OutBuffer.append("\n")
        
    def doClientRead(self):
        if self.ReadClosed:
            return

        try:    
            data = self.CSock.recv(self.MAXMSG)
            data = data.decode("utf-8")
        except: 
            data = ""
        
        #print("data:[{}]".format(data))
    
        if data:
            if not self.Request:
                self.addToRequest(data)
            else:
                self.addToBody(data)
        else:
            self.ReadClosed = True

        if self.ReadClosed and not self.Request:
            self.shutdown()
                    
    def doWrite(self):
        #print ("doWrite: outbuffer:", len(self.OutBuffer))
        if self.OutBuffer:
            line = self.OutBuffer[0]
            try:
                if isinstance(line, str):
                    line = bytes(line, "utf-8")
                sent = self.CSock.send(line)
            except: 
                sent = 0
            self.BytesSent += sent
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
            self.Server.log(self.CAddr, self.RequestMethod, self.URL, self.ResponseStatus, self.BytesSent)
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

    def __init__(self, port, app, url_pattern="*", max_connections = 100, enabled = True, max_queued = 100,
                logging = True, log_file = None):
        PyThread.__init__(self)
        #self.debug("Server started")
        self.Port = port
        self.WSGIApp = app
        self.Match = url_pattern
        self.Enabled = False
        self.Logging = logging
        self.LogFile = sys.stdout if log_file is None else log_file
        self.Connections = TaskQueue(max_connections, capacity = max_queued)
        if enabled:
            self.enableServer()
        
    @synchronized
    def log(self, caddr, method, uri, status, bytes_sent):
        self.LogFile.write("{}: {} {} {} {} {}\n".format(
                time.ctime(), caddr[0], method, uri, status, bytes_sent
        ))
        if self.LogFile is sys.stdout:
            self.LogFile.flush()

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

    def connectionClosed(self, conn):
        pass
            
    @synchronized
    def connectionCount(self):
        return len(self.Connections)    
            
    def run(self):
        self.Sock = socket(AF_INET, SOCK_STREAM)
        self.Sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
        self.Sock.bind(('', self.Port))
        self.Sock.listen(10)
        while True:
            csock, caddr = self.Sock.accept()
            self.Connections << HTTPConnection(self, csock, caddr)
                
                
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
