from BaseHTTPServer import HTTPServer
import Queue
from SimpleHTTPServer import SimpleHTTPRequestHandler
from SocketServer import ThreadingMixIn
from cgi import  FieldStorage
import pika
import threading
import time
import uuid
import requests

from interface_pb2 import WorkRequest
import json


import cgitb
try:
    from cStringIO import StringIO
except:
    from StringIO import StringIO


# RabbitMQ connection information
address='pchradis.fit.vutbr.cz'
port=5672
user='testing'
password='its'

serveraddr = ('', 8888) #port on which to listen



class receiverThread( threading.Thread):
    """
    Thread that accepts AMQP messages and passes them to registered listeners
    """
    
    def __init__(self, callback_queue, requestQueue, lock, address='localhost', port=5672, user='quest', password='quest'):
        """
        Constructor.
        
        @param callback_queue a list which is appended with  return queue name where this receiver listens
        @param requestQueue a python queue where clients send  
        """
        threading.Thread.__init__(self)

        self.requestQueue = requestQueue
        self.requests = {}
        self.requestLock = threading.Lock()
        
        self.connection = pika.BlockingConnection( 
             pika.ConnectionParameters( address, port, '/', 
                 pika.PlainCredentials( user, password)))

        self.channel = self.connection.channel()
        result = self.channel.queue_declare(exclusive=True)
        self.callback_queue = result.method.queue
        self.channel.basic_consume( self.on_response, no_ack=True,
                                   queue=self.callback_queue)   

        callback_queue.append( self.callback_queue)
        lock.release()

    def registerRequests(self, requests):
        self.requestLock.acquire()
        for k in requests.keys():
            self.requests[ k] = requests[k]   
        self.requestLock.release()  

    def on_response(self, ch, method, props, body):

        #TODO - fix requsts locking - this code should not work
        if props.correlation_id in self.requests.keys():
            self.requests[props.correlation_id].put( body)
            self.requests.pop( props.correlation_id)        
        else:
            print " [x] Wrong correlation_id"
        
    def run( self):
        while True:
            self.connection.process_data_events() 


class senderThread( threading.Thread):
    """
    Thread that reads messages from a queue and sends them.
    """
    
    def __init__(self, inputQueue, address='localhost', port=5672, user='quest', password='quest'):
        """
        Constructor.
        
        @param inputQueue  python queue where others can push messages
        """

        threading.Thread.__init__(self)

        self.connection = pika.BlockingConnection( 
             pika.ConnectionParameters( address, port, '/', 
                 pika.PlainCredentials( user, password)))
        self.channel = self.connection.channel()   
        self.inputQueue = inputQueue

    def run( self):
        while True:
            request = self.inputQueue.get( block=True)
            self.channel.basic_publish(exchange=request['exchange'],
                                   routing_key=request['routing_key'],
                                   properties=pika.BasicProperties(
                                         reply_to = request['reply_to'],
                                         correlation_id = request['correlation_id'],
                                         ),
                                   body=request['body'])

class ServerHanlder( SimpleHTTPRequestHandler):

    defaultConfiguration = "default_config"
    requestTimeout = 6
    caffeConfigPath = "./caffe/"

    # serves files from current folder# Catch a Keyboard Interrupt to make sure that the connection is closed cleanly
    def do_GET( self):
        SimpleHTTPRequestHandler.do_GET( self)
    
    def packMessage(self, iamgeData, configFile):
        pass
    
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
    
    def buildRequest(self, request, image):    
        request.uuid = str(uuid.uuid4())
        request.timestamp = time.time()
        request.image = image
        request.returnQueue = callback_queue_name
        return request
             
    # custom POST handling
    def do_POST( self):
        try:
            sTime = time.time()

            self.getRequestDataFromClient()
            form = self.parsePOSTContent()
            
            if self.path == '/tagging':
                configurationName = self.caffeConfigPath + self.getConfigurationName( form)
                configuration = self.getConfiguration( configurationName)
                if 'url' in form:
                    response = requests.get( form['url'].value)
                    request = self.buildRequest( configuration, response.content) 
                else:
                    request = self.buildRequest( configuration, form['file'].value)    
              
                responseQueue = Queue.Queue();
                receiver.registerRequests( { request.uuid: responseQueue })
                senderQueue.put( { 'exchange': '', 
                            'routing_key': request.configuration[0].queue, 
                            'reply_to': callback_queue_name,
                            'correlation_id': request.uuid,
                            'body': request.SerializeToString()})
                
                response = responseQueue.get( block=True, timeout=ServerHanlder.requestTimeout)
                self.sendResponse(response)
                
                print "DONE in ", str( time.time() - sTime)
                return
                
                
                
            # process data
            if form.has_key('file'):

                configurationName = self.getConfigurationName( form)
                configuration = self.getConfiguration( configurationName)
                request = self.buildRequest( configuration, form['file'].value)    
              
                responseQueue = Queue.Queue();
                receiver.registerRequests( { request.uuid: responseQueue })
                senderQueue.put( { 'exchange': '', 
                            'routing_key': 'rpc_queue', 
                            'reply_to': callback_queue_name,
                            'correlation_id': request.uuid,
                            'body': request.SerializeToString()})
                
                response = responseQueue.get( block=True, timeout=ServerHanlder.requestTimeout)
                self.sendResponse(response)
                
                print "DONE in ", str( time.time() - sTime)
                return
           
            self.send_response( 400, "Wrong request format.")
                
        except IOError, e:
            print "XXXX", e
            self.send_response( 400, str( e))
        except Exception, e:
            print "YYYY",  e 
            self.send_response( 400, "Exeption")

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


receiver = receiverThread( callback_queue=callback_queue, requestQueue=receiverQueue, 
    address=address, port=port, user=user, password=password, lock=lock)
lock.acquire()
callback_queue_name = callback_queue[0]

senderQueue = Queue.Queue();
sender = senderThread( inputQueue=senderQueue, 
    address=address, port=port, user=user, password=password,)

sender.start();
receiver.start();


cgitb.enable()
srvr = ThreadingServer( serveraddr, ServerHanlder)

#connection()
srvr.serve_forever()
