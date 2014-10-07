from PIL import Image
try:
    from cStringIO import StringIO
except:
    from StringIO import StringIO
from RPCConnection import RPCConnection 

address='localhost'
port=5672
user='testing'
password='its'
inputQueue='resize_queue'

class ExampleRequest( object):
    def __init__( self, idString):
        self.idString = idString
        
    def on_request( self, request):
        print " [x] DO ", self.idString
         
        im = Image.open( StringIO( request.image))
	newSize = [ int( s * request.configuration[0].resize.ratio) for s in im.size]
        print im.size, newSize
        im = im.resize( newSize)
        print im.size, newSize

        buffer = StringIO()
        im.save( buffer, format='JPEG')
        request.image = buffer.getvalue()
    
print " [x] Init connection"
connection = RPCConnection(  ExampleRequest("TEST_Callback").on_request, address, port, user, password, inputQueue)
print " [x] Awaiting RPC requests"
connection.start()
print " [x] Connection terminated"

