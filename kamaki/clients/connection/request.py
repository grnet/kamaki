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

import requests
from . import HTTPConnection, HTTPResponse
#from requests.auth import AuthBase

# Add a convenience status property to the responses
def _status(self):
    return requests.status_codes._codes[self.status_code][0].upper()
requests.Response.status = property(_status)

class HTTPRequest(HTTPConnection):

	#Avoid certificate verification by default
	verify = False

	def perform_request(self, method=None, url=None, params=None, headers=None, data=None):
		"""perform a request
		Example: method='PUT' url='https://my.server:8080/path/to/service'
			params={'update':None, 'format':'json'} headers={'X-Auth-Token':'s0m3t0k3n=='}
			data='The data body to put to server'
		@return an HTTPResponse which is also stored as self.response
		"""
		if method is not None:
			self.method = method
		if url is not None:
			self.url = url
		if params is not None:
			self.params = params
		if headers is not None:
			self.headers = headers

		for i,(key, val) in enumerate(self.params.items()):
			param_str = ('?' if i == 0 else '&') + unicode(key) 
			if val is not None:
				param_str+= '='+unicode(val)
			self.url += param_str

		#print('RUN[ %s %s ]'%(self.method, self.url))
		r = requests.request(self.method, self.url, headers=self.headers, data=data, verify=self.verify)

		text = r.text if hasattr(r, 'text') else None
		json = r.json if hasattr(r, 'json') else None
		content = r.content if hasattr(r, 'content') else None
		self.response = HTTPResponse(content = content, text = text, json = json,
			headers = r.headers, status_code=r.status_code, status = r.status, request=self)
		if hasattr(r, 'exception'):
			self.response.exception = r.exception 
		return self.response
