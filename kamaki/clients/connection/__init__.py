# Copyright 2011-2012 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or
# without modification, are permitted provided that the following
# conditions are met:
#
#   1. Redistributions of source code must retain the above
#      copyright notice, self.list of conditions and the following
#      disclaimer.
#
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, self.list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY GRNET S.A. ``AS IS'' AND ANY EXPRESS
# OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL GRNET S.A OR
# CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF
# USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED
# AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and
# documentation are those of the authors and should not be
# interpreted as representing official policies, either expressed
# or implied, of GRNET S.A.

class HTTPResponse(object):
	def __init__(self, content=None, text = None, json = None, headers = None, status_code=0, status='',
		request=None):
		self.content = content #content in bytes
		self.text = text #content in text
		self.json = json #content in json
		self.headers = headers #content headers
		self.status_code = status_code
		self.status = status
		self.request=request

class HTTPConnectionError(Exception):
    def __init__(self, message, status=0, details=''):
    	super(HTTPConnectionError, self).__init__(message)
        self.message = message
        self.status = status
        self.details = details

class HTTPConnection(object):

    def __init__(self, method=None, url=None, params={}, headers={}):
    	self.response = None
    	self.headers = headers
    	self.params = params
    	self.url = url
    	self.method = method

    def raise_for_status(self, r):
        message = "%d %s" % (r.status_code, r.status)
        try:
            details = r.text
        except:
            details = ''
        raise HTTPConnectionError(message, r.status_code, details)

    def set_header(self, name, value):
    	self.headers[unicode(name)] = unicode(value)

    def remove_header(self, name):
    	try:
    		self.headers.pop(name)
    	except KeyError:
    		pass

    def replace_headers(self, new_headers):
    	self.headers = new_headers

    def reset_headers(self):
    	self.replace_headers({})

    def set_param(self, name, value=None):
    	self.params[name] = value

    def remove_param(self, name):
    	try:
    		self.params.pop(name)
    	except KeyError:
    		pass

    def replace_params(self, new_params):
    	self.params = new_params

    def reset_params(self):
    	self.replace_params({})

    def set_url(self, url):
    	self.url = url

    def set_method(self, method):
    	self.method = method

	def perform_request(self, method=None, url=None, params=None, headers=None, data=None):
		"""
		@return an HTTPResponse (also in self.response of this object)
		named args offer the ability to reset a request or a part of the request
		e.g. r = HTTPConnection(url='http://....', method='GET')
			 r.perform_request()
			 r.perform_request(method='POST')
		will perform a GET request and later a POST request on the same URL
		another example:
			 r = HTTPConnection(url='http://....', params='format=json')
			 r.perform_request(method='GET')
			 r.perform_request(method='POST')
		"""
		raise NotImplementedError
