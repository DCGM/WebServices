import numpy as np
import time
import scipy.io
import skimage
import os
from PIL import Image
try:
    from cStringIO import StringIO
except:
    from StringIO import StringIO

import caffe

from interface_pb2 import WorkRequest, ResultList
import RPCConnection
from SimilarSearcher import SimilarSearcher


#network RPC configuration
address='pchradis.fit.vutbr.cz'
port=5672
user='testing'
password='its'
inputQueue='caffe_search_queue'

dataPath = "../data/RTR/"
model_def        = os.path.join( dataPath, "RTR_deploy_fc6.prototxt")
pretrained_model = os.path.join( dataPath, "RTR_iter_25000")
mean_file        = os.path.join( dataPath, "ilsvrc_2012_mean.npy")
modelFile        = os.path.join( dataPath, "PROD256.fc6")
modelURLFile     = os.path.join( dataPath, "PROD256.list")

imageDim = 256
image_dims = [ imageDim, imageDim]
gpu = True
input_scale = 255
channel_swap = [2,1,0]

print "[x] Make classifier"
classifier = caffe.Classifier(model_def, pretrained_model,
            image_dims=image_dims, gpu=gpu, mean=np.load( mean_file),
            input_scale=input_scale, channel_swap=channel_swap)

print "[x] Read models data"
modelURL = [x.strip() for x in open( modelURLFile)]
modelData = np.loadtxt( modelFile)

print "[x] L2 normalize data"
for r in range( modelData.shape[0]):
    modelData[ r, :] = 1.0 / np.sqrt( modelData[ r, :].dot( modelData[ r, :].T)) * modelData[ r, :]

print "[x] Init request handler"
searcher = SimilarSearcher( classifier, imageDim, modelData, modelURL)

print " [x] Init connection"
connection = RPCConnection.RPCConnection(  searcher.on_request, address, port, user, password, inputQueue)

print " [x] Awaiting RPC requests"
connection.start()
print " [x] Connection terminated"
