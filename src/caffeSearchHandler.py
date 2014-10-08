import json
import requests

class CaffeSearchHandler:
    configPath = "./caffeSearch/"
    
    def createRequest(self, form, workRequest ):
        if 'url' in form:
            image = requests.get( form['url'].value).content
        else:
            image = form['file'].value
        workRequest.image = image

        self.queryName = 'queries/' + str(workRequest.uuid) + '.jpg'
        with open( self.queryName, 'w') as f:
            f.write( image)


    def createImageTiles( self, url):
      images = [ '<img src="%s">' % x for x in url]
      return "\n".join( images)


    def createResponse( self, responseHandler, responseMessage):
        if responseHandler.path == '/search':
            responseText = self.createImageTiles( responseMessage.result.url)
            with open( 'caffeSearch.html','r') as f:
                formHTML = f.read()

            responseHandler.send_response(200, 'OK')
            responseHandler.send_header('Content-type', 'text/html')
            responseHandler.end_headers()
            responseHandler.wfile.write( formHTML)
            responseHandler.wfile.write( '<img src="%s">' % self.queryName)
            responseHandler.wfile.write( responseText)
        else:
	    responseList = [ 
                {'id': i, 'score': request.result.score[i],  
                 'url': request.result.url[i] 
                } for i in range( len( score))]
	    responseJson = json.dumps( responseList)
	    responseHandler.send_response(200, 'OK')
	    responseHandler.send_header('Content-type', 'application/json')
	    responseHandler.end_headers()
	    responseHandler.wfile.write( responseJson)


