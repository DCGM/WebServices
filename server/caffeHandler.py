import requests
import json

class CaffeHandler:
    configPath = "caffe"
    
    def createRequest(self, form, workRequest ):
        if 'url' in form:
            image = requests.get( form['url'].value).content
        else:
            image = form['file'].value
        workRequest.image = image

    def createResponse( self, responseHandler, responseMessage):
        responseList = self.createResponseList( responseMessage.result.score, responseMessage.result.url)
        responseJson = json.dumps( responseList)

        responseHandler.send_response(200, 'OK')
        responseHandler.send_header('Content-type', 'application/json')
        responseHandler.end_headers()
        responseHandler.wfile.write( responseJson)

    def createResponseList(self, score, url):
        results = []
        for i in range( len( score)):
            results.append({'id': i, 'score': score[i], 'url': url[i] })
        return results
