import sys

import foolscap

url = ''

if sys.argv[1] == 'server1':
    from twisted.internet import reactor
    from foolscap.api import Referenceable, UnauthenticatedTub
    
    class MathServer(Referenceable):
        def remote_add(self, a, b):
            return a+b#/0
        def remote_subtract(self, a, b):
            return a-b
    
    myserver = MathServer()
    tub = UnauthenticatedTub()
    tub.listenOn("tcp:12345")
    tub.setLocation("localhost:12345")
    url = tub.registerReference(myserver, "math-service")
    print "the object is available at:", url
    
    tub.startService()
    reactor.run()
    
if sys.argv[1] == 'server2':
    from twisted.internet import reactor
    from foolscap.api import Referenceable, Tub
    
    class MathServer(Referenceable):
        def remote_add(self, a, b):
            return a+b
        def remote_subtract(self, a, b):
            return a-b
    
    myserver = MathServer()
    tub = Tub(certFile="pb2server.pem")
    tub.listenOn("tcp:12345")
    tub.setLocation("localhost:12345")
    url = tub.registerReference(myserver, "math-service")
    print "the object is available at:", url
    
    tub.startService()
    reactor.run()


elif sys.argv[1].startswith('client'):
    from twisted.internet import reactor
    from foolscap.api import Tub
    
    def gotError1(why):
        print "unable to get the RemoteReference:", why
        reactor.stop()
    
    def gotError2(why):
        print "unable to invoke the remote method:", why
        print type(why)
        print why.__name__
        reactor.stop()
    
    def gotReference(remote):
        print "got a RemoteReference"
        print "asking it to add 1+2"
        d = remote.callRemote("add", a=1, b=2)
        d.addCallbacks(gotAnswer, gotError2)
    
    def gotAnswer(answer):
        print "the answer is", answer
        reactor.stop()
    
    if sys.argv[1].endswith('1'):
        url = 'pbu://localhost:12345/math-service'
    else:
        url = sys.argv[2]
        
    tub = Tub()
    tub.startService()
    d = tub.getReference(url)
    d.addCallbacks(gotReference, gotError1)
    
    reactor.run()
else:
    print 'unknown arg', argv[1]

