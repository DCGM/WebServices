import RPCConnection
import numpy as np
import os
import sys
import argparse
import glob
import time
import scipy.io
import caffe
import skimage

from PIL import Image
from interface_pb2 import WorkRequest, ResultList
try:
    from cStringIO import StringIO
except:
    from StringIO import StringIO

#network RPC configuration
address='pchradis.fit.vutbr.cz'
port=5672
user='testing'
password='its'
inputQueue='SUN397_queue'

data_path = "../data/SUN397/"

#load synset definitions
classFile = os.path.join( data_path, "classes.txt")
with open( classFile, "r") as f:
    synsets = f.read().split()

model_def = os.path.join( data_path, "deploy.prototxt")
pretrained_model = os.path.join( data_path, "SUN397_iter_90000.caffemodel")

image_dims = [256,256]
gpu = True
mean_file = os.path.join( data_path, 'ilsvrc_2012_mean.npy')
input_scale = 255
channel_swap = [2,1,0]

class ClasificationRequest( object):
    def __init__( self, classifier):
        self.classifier = classifier

    def on_request( self, request):
        print "have request"
        imgData = request.image
        im = Image.open( StringIO( imgData))
        im.resize((256,256), Image.ANTIALIAS)

        np_image=np.asarray(im)

        color = True

        img = skimage.img_as_float(np_image/255.).astype(np.float32)
        if img.ndim == 2:
            img = img[:, :, np.newaxis]
            if color:
                img = np.tile(img, (1, 1, 3))
            elif img.shape[2] == 4:
                img = img[:, :, :3]

        # Classify.
        center_only = False
        predictions = self.classifier.predict([img], not center_only)
        print predictions

        request.ClearField('image')

        #detected classes are last
        order = predictions.argsort().tolist()[0]
        order.reverse()
        predictions = predictions.tolist()[0]
        
        for i in order[ 0:request.configuration[0].caffe.resultSize]:
            request.result.url.append( synsets[ i])
            request.result.score.append( predictions[ i])


print " [x] Create classifier"
classifier = caffe.Classifier(model_def, pretrained_model,
            image_dims=image_dims, gpu=gpu, mean=np.load( mean_file),
            input_scale=input_scale, channel_swap=channel_swap)


print " [x] Create request handler"
classification_request=ClasificationRequest( classifier)

print " [x] Init connection"
connection = RPCConnection.RPCConnection(  classification_request.on_request, address, port, user, password, inputQueue)
print " [x] Awaiting RPC requests"
connection.start()
print " [x] Connection terminated"
