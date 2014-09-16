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
inputQueue='caffe_queue'

pycaffe_dir = "/home/ihradis/cuda-workspace/caffe/python/";

#load synset definitions
synsets = scipy.io.loadmat('../data/synsets.mat')

model_def = os.path.join(pycaffe_dir,
                "../examples/imagenet/imagenet_deploy.prototxt")
pretrained_model = os.path.join(pycaffe_dir,
                "../examples/imagenet/caffe_reference_imagenet_model")
image_dims = [256,256]
gpu = True
mean_file = os.path.join(pycaffe_dir,'caffe/imagenet/ilsvrc_2012_mean.npy')
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

        #this order is offset from Matlab's, because it starts at 0.
        #also, detected classes are last
        order = predictions.argsort()

        request.ClearField('image')
        
        for i in range( request.configuration[0].caffe.resultSize):
            #accessing the matlab struct is unnatural, but works. Speed not verified
            request.result.url.append( synsets['synsets'][0][order[0][order.shape[1]-1-i]][2][0])
            request.result.score.append( np.asscalar(predictions[0][order[0][order.shape[1]-1-i]]))








# Make classifier.
classifier = caffe.Classifier(model_def, pretrained_model,
            image_dims=image_dims, gpu=gpu, mean_file=mean_file,
            input_scale=input_scale, channel_swap=channel_swap)

classification_request=ClasificationRequest( classifier)

print " [x] Init connection"
connection = RPCConnection.RPCConnection(  classification_request.on_request, address, port, user, password, inputQueue)
print " [x] Awaiting RPC requests"
connection.start()
print " [x] Connection terminated"
