from threading import RLock, Thread, Event

Waiting = []
In = []

def synchronized_with_monitor(method):
    def smethod(self, *params, **args):
        #print "@synchronized: wait %s..." % (method,)
        q = "%s(%x).%s" % (self, id(self), method)
        Waiting.append(q)
        with self:
            Waiting.remove(q)
            #print "@synchronized: in %s" % (method,)
            In.append(q)
            out = method(self, *params, **args)
        #print "@synchronized: out %s" % (method,)
        In.remove(q)
        return out
    return smethod

def synchronized(method):
    def smethod(self, *params, **args):
        with self:
            return method(self, *params, **args)
    return smethod

def printWaiting():
    print "waiting:----"
    for w in Waiting:
        print w
    print "in:---------"
    for w in In:
        print w

class Lockable:
    def __init__(self):
        self._Lock = RLock()

    def __enter__(self):
        return self._Lock.__enter__()
        
    def __exit__(self, exc_type, exc_value, traceback):
        return self._Lock.__exit__(exc_type, exc_value, traceback)

    def acquire(self, *params, **args):
        return self._Lock.acquire(*params, **args)
        
    def release(self):
        return self._Lock.release()

class MyThread(Thread, Lockable):
    def __init__(self):
        Thread.__init__(self)
        Lockable.__init__(self)
