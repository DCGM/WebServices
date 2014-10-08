import threading

import pika

from interface_pb2 import WorkRequest, ResultList


class RPCConnection( object):
    def __init__( self, callback, address='localhost', port=5672, user='testing',
        password='its', inputQueue='rpc_queue'):

        self.callback = callback
        self.connection = pika.BlockingConnection(
             pika.ConnectionParameters( address, port, '/',
                 pika.PlainCredentials( user, password)))

        self.channel = self.connection.channel()
        self.inputQueue = inputQueue
        self.channel.queue_declare( queue=inputQueue)        
        self.channel.basic_qos(prefetch_count=1)

        self.channel.basic_consume( self.on_request, queue=inputQueue)        

                     
    def on_request(self, ch, method, props, body):
        request = WorkRequest()
        request.ParseFromString( body)
        
        try:
          self.callback( request)
        except Exception, e:
          print e   #TODO: should handle errors better (error code + error message)

        # remove current configuration from queue
        request.pastConfiguration.add().CopyFrom( request.configuration[0])
        request.configuration.remove( request.configuration[0])
        
        if len( request.configuration) > 0:
            nextKey = request.configuration[0].queue
        else:
            nextKey = request.returnQueue
        
        ch.basic_publish(exchange='',
             routing_key=nextKey,
             properties=pika.BasicProperties(correlation_id = props.correlation_id,
                                             reply_to=props.reply_to
                                             ),
             body= request.SerializeToString())
    
        ch.basic_ack( delivery_tag = method.delivery_tag)        
        print "DONE ", props.correlation_id, " ",  props.reply_to

    def start( self):
        self.channel.start_consuming()


class ReceiverThread( threading.Thread):
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


class SenderThread( threading.Thread):
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
