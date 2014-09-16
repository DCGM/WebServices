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
        except:
          pass
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
