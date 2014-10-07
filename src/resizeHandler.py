class ResizeHandler:
    configPath = "./resize/"
    
    def createRequest(self, form, workRequest ):
        workRequest.image = form['file'].value
        if 'ratio' in form:
           workRequest.configuration[0].resize.ratio = float( form['ratio'].value)

    def createResponse( self, responseHandler, responseMessage):
        responseHandler.send_response(200, 'OK')
        responseHandler.send_header('Content-type', 'image/jpeg')
        responseHandler.end_headers()
        responseHandler.wfile.write( responseMessage.image)
