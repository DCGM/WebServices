from PIL import Image
try:
    from cStringIO import StringIO
except:
    from StringIO import StringIO
import RPCConnection

address='localhost'
port=5672
user='testing'
password='its'
inputQueue='rpc_queue'

class ExampleRequest( object):
    def __init__( self, idString):
        self.idString = idString
        
    def on_request( self, request):
        print " [x] DO ", self.idString
         
        imgData = request.image
        im = Image.open( StringIO( imgData))
        im.resize( (32, 32))
        request.ClearField('image')
        
        for i in range( request.configuration[0].match.listSize):
            request.result.url.append( 'http://www.cosi.cz/%s.png' % str(i ))
            request.result.score.append( i)
    
print " [x] Init connection"
connection = RPCConnection(  ExampleRequest("TEST_Callback").on_request, address, port, user, password, inputQueue)
print " [x] Awaiting RPC requests"
connection.start()
print " [x] Connection terminated"

