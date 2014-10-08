import Queue
import threading
import time
import uuid
import re
import json
import cgitb
from BaseHTTPServer import HTTPServer
from SimpleHTTPServer import SimpleHTTPRequestHandler
from SocketServer import ThreadingMixIn
from cgi import FieldStorage
try:
    from cStringIO import StringIO
except:
    from StringIO import StringIO

import pika

from RPCConnection import ReceiverThread, SenderThread
from interface_pb2 import WorkRequest
from caffeHandler import CaffeHandler 
from caffeSUN397Handler import CaffeSUN397Handler 
from caffeSearchHandler import CaffeSearchHandler 
from resizeHandler import ResizeHandler

# RabbitMQ connection information
address='pchradis.fit.vutbr.cz'
port=5672
user='testing'
password='its'

#port on which to listen
serveraddr = ('', 8888) 



class ServerHanlder( SimpleHTTPRequestHandler):

    defaultConfiguration = "default_config"
    requestTimeout = 6
    
    def registerHandlers( self):
        self.handlers = []
        self.registerHandler( "/resize$", ResizeHandler())
        self.registerHandler( "/tagging$", CaffeHandler())
        self.registerHandler( "/sun397$", CaffeSUN397Handler())
        self.registerHandler( "/search/json$|/search$", CaffeSearchHandler())

    def registerHandler( self, path, handler):
        self.handlers.append( (re.compile( path) , handler))
    
    # serves files from current folder
    # Catch a Keyboard Interrupt to make sure that the connection is closed cleanly
    def do_GET( self):
        SimpleHTTPRequestHandler.do_GET( self)
    
    def getRequestDataFromClient(self):
        # the client can wait with sending of data until server sends this (curl does this)
        if 'expect' in self.headers and self.headers['expect'] == '100-continue':
            # self.send_response( 100) 
            self.wfile.write( 'HTTP/1.1 100 Continue\n\n')
    
    def getConfiguration(self, confID):
        f = open( confID + ".protobin", "r")
        config = WorkRequest()
        config.ParseFromString( f.read())
        f.close()
        return config
    
    def parsePOSTContent(self):
        form =  FieldStorage(
                fp=self.rfile, 
                headers=self.headers,
                environ={'REQUEST_METHOD':'POST',
                         'CONTENT_TYPE':self.headers['Content-Type'],
                         })
        return form
    
    def createResponseList(self, score, url):
        results = []
        for i in range( len( score)):
            results.append({'id': i, 'score': score[i], 'url': url[i] })
        return results

   
    def sendResponse(self, response):
        request = WorkRequest()
        request.ParseFromString( response)
        
        responseList = self.createResponseList( request.result.score, request.result.url)
        responseJson = json.dumps( responseList)
        
        self.send_response(200, 'OK')
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write( responseJson)
     
    def getConfigurationName(self, form):
        return form.getvalue( 'configuration', ServerHanlder.defaultConfiguration)
    
    def buildRequest(self, request, image=''):    
        request.uuid = str(uuid.uuid4())
        request.timestamp = time.time()
        request.image = image
        request.returnQueue = callback_queue_name
        return request

    def sendRequest( self, request):
        responseQueue = Queue.Queue();
        receiver.registerRequests( { request.uuid: responseQueue })
        senderQueue.put( { 'exchange': '', 
                        'routing_key': request.configuration[0].queue, 
                        'reply_to': callback_queue_name,
                        'correlation_id': request.uuid,
                        'body': request.SerializeToString()})
        return responseQueue

             
    def createImageTiles( self, url):
      images = [ '<img src="%s">' % x for x in url]
      return "\n".join( images)

    # custom POST handling
    def do_POST( self):
        sTime = time.time()
        print self.path
        try:
            self.registerHandlers()

            self.getRequestDataFromClient()
            form = self.parsePOSTContent()
                
            for handler in self.handlers:
                if handler[0].match( self.path):
                   configurationName =  handler[1].configPath + self.getConfigurationName( form)
                   configuration = self.getConfiguration( configurationName)
                   request = self.buildRequest( configuration)
                   
                   handler[1].createRequest( form, workRequest=request)
              
                   responseQueue = self.sendRequest( request)
                
                   responseStr = responseQueue.get( block=True, timeout=ServerHanlder.requestTimeout)
                   response = WorkRequest()
                   response.ParseFromString( responseStr)
                   
                   handler[1].createResponse( self, response)
                   break
            else:  
                self.send_response( 400, "Wrong request format.")

        finally:
           print "%s in %s" % (self.path, str(time.time() - sTime))
        """except IOError, e:
            print "XXXX", e
            self.send_response( 400, str( e))
        except Exception, e:
            print "YYYY",  e 
            self.send_response( 400, "Exeption")"""


# multi-threaded server class
class ThreadingServer( ThreadingMixIn, HTTPServer):
    pass

global callback_queue_name
global senderQueue
global receiver


#prepare communication threads
lock = threading.Lock()
lock.acquire()
callback_queue = []
receiverQueue=Queue.Queue()


receiver = ReceiverThread( callback_queue=callback_queue, requestQueue=receiverQueue, 
    address=address, port=port, user=user, password=password, lock=lock)
lock.acquire()
callback_queue_name = callback_queue[0]

senderQueue = Queue.Queue();
sender = SenderThread( inputQueue=senderQueue, 
    address=address, port=port, user=user, password=password,)

sender.start();
receiver.start();


cgitb.enable()
srvr = ThreadingServer( serveraddr, ServerHanlder)

#connection()
srvr.serve_forever()
