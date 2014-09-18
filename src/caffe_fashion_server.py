import RPCConnection
import numpy as np
import time
import scipy.io
import caffe
import skimage
import os

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

class SimilarSearcher( object):
    def __init__( self, classifier, modelData="", modelURL=""):
        self.classifier = classifier
        self.modelData = modelData
        self.modelURL = modelURL
        
    def on_request( self, request):
        print "have request"
        imgData = request.image
        im = Image.open( StringIO( imgData))

        order, distances = self.do_work( im)

        request.ClearField('image')
        for i in range( request.configuration[0].caffeSearch.resultSize):
            print order[0, i]," ", distances[ 0, i]
            request.result.url.append( self.modelURL[ order[0, i]])
            request.result.score.append( distances[ 0, i])

    def do_work( self, image):

        predictions = self.processImage( image)

        #print predictions.tolist()
        predictions = 1.0 / np.sqrt(predictions.dot( predictions.T))[0] * predictions

        distances = 1-self.modelData.dot( predictions.T).T
        order = np.argsort( distances)
        distances = distances[ 0, order]

        return (order, distances)
    
    def processImage( self, image):
        scale = imageDim * 1.0 / max(image.size)
        scaledSize = [ int( round( scale * x)) for x in image.size]
    
        image = image.resize( scaledSize, Image.ANTIALIAS)  #TODO: This resize is really slow for large images

        np_image = np.asarray(image)

        #add borders
        meanVal = np_image.mean();

        left = np.empty( (np_image.shape[0], (image_dims[1] - np_image.shape[1])/2, 3));
        left.fill( meanVal);
        np_image = np.concatenate( (left, np_image), axis=1)

        right = np.empty( (np_image.shape[0], image_dims[1] - np_image.shape[1], 3));
        right.fill( meanVal);
        np_image = np.concatenate( (np_image, right), axis=1)

        top = np.empty( ((image_dims[0] - np_image.shape[0])/2, np_image.shape[1], 3));
        top.fill( meanVal)
        np_image = np.concatenate( (top, np_image), axis=0)

        bottom = np.empty( (image_dims[0] - np_image.shape[0], np_image.shape[1], 3));
        bottom.fill( meanVal)
        np_image = np.concatenate( ( np_image, bottom), axis=0)
        
        color = True

        img = skimage.img_as_float( np_image / 255.).astype( np.float32)
        if img.ndim == 2:
            img = img[:, :, np.newaxis]
            if color:
                img = np.tile(img, (1, 1, 3))
            elif img.shape[2] == 4:
                img = img[:, :, :3]

        # Classify.
        return self.classifier.predict([img], oversample=True)


# Make classifier.
classifier = caffe.Classifier(model_def, pretrained_model,
            image_dims=image_dims, gpu=gpu, mean_file=mean_file,
            input_scale=input_scale, channel_swap=channel_swap)

# Read models data
modelURL = [x.strip() for x in open( modelURLFile)]
modelData = np.loadtxt( modelFile)
#L2 normalize data
for r in range( modelData.shape[0]):
    modelData[ r, :] = 1.0 / np.sqrt( modelData[ r, :].dot( modelData[ r, :].T)) * modelData[ r, :]



searcher = SimilarSearcher( classifier, modelData, modelURL)

"""with open( 'first.png') as f:
    image = Image.open( f)
    searcher.do_work( image)
"""

print " [x] Init connection"
connection = RPCConnection.RPCConnection(  searcher.on_request, address, port, user, password, inputQueue)
print " [x] Awaiting RPC requests"
connection.start()
print " [x] Connection terminated"
