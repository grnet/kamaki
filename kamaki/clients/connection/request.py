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
from copy import deepcopy
from . import HTTPConnection, HTTPResponse, HTTPConnectionError
#from requests.auth import AuthBase

# Add a convenience status property to the responses
def _status(self):
    return requests.status_codes._codes[self.status_code][0].upper()
requests.Response.status = property(_status)

class HTTPRequestsResponse(HTTPResponse):

	def __init__(self, requestsResponse, prefetched = False):
		try:
			self.headers = requestsResponse.headers
			self.text = requestsResponse.text if hasattr(requestsResponse, 'text') else None
			self.json = requestsResponse.json if hasattr(requestsResponse, 'json') else None
			self.content = requestsResponse.content if hasattr(requestsResponse, 'content') else None
			self.exception = requestsResponse.exception if hasattr(requestsResponse, 'exception') else None
			self.status = requestsResponse.status
			self.status_code = requestsResponse.status_code
		except requests.ConnectionError as err:
			raise HTTPConnectionError('Connection error', status=651, details=err.message)
		except requests.HTTPError as err:
			raise HTTPConnectionError('HTTP error', status=652, details=err.message)
		except requests.Timeout as err:
			raise HTTPConnectionError('Connection Timeout', status=408, details=err.message)
		except requests.URLRequired as err:
			raise HTTPConnectionError('Invalid URL', status=404, details=err.message)
		except requests.RequestException as err:
			raise HTTPConnectionError('HTTP Request error', status=700, details=err.message)

	def _get_response(self):
		"""requests object handles this automatically"""
		pass

class HTTPRequest(HTTPConnection):

	#Avoid certificate verification by default
	verify = False

	def _copy_response(self):
		req = HTTPRequest(deepcopy(self.method), deepcopy(self.url), deepcopy(self.params),
			deepcopy(self.headers))
		req._response_object = self._response_object
		res = HTTPResponse(req)
		return res

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

		self._response_object = requests.request(self.method, self.url, headers=self.headers, data=data,
			verify=self.verify, prefetch = False)
		res  = HTTPRequestsResponse(self._response_object)
		self.response = res
		return res
