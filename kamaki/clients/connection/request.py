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
from kamaki.clients.connection import HTTPConnection, HTTPResponse, HTTPConnectionError
from kamaki.clients.connection.pool import ObjectPool
from urlparse import urlparse

# Add a convenience status property to the responses
def _status(self):
	return requests.status_codes._codes[self.status_code][0].upper()
requests.Response.status = property(_status)

class HTTPRequestsResponse(HTTPResponse):

	def __init__(self, request=None, prefetched=False):
		super(HTTPRequestsResponse, self).__init__(request=request, prefetched=prefetched)
		if prefetched:
			self = request.response

	def _get_response(self):
		if self.prefetched:
			return
		r = self.request.response
		try:
			self.headers = r.headers
			self.status = r.status
			self.status_code = r.status_code
			self.content = r.content if hasattr(r, 'content') else None
			from json import loads
			try:
				self.json = loads(r.content)#None if self._get_content_only else r.json
			except ValueError:
				self.json = None
			self.text = r.content#None if self._get_content_only else r.text
			self.exception = r.exception if hasattr(r, 'exception') else None
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
		self.prefetched=True

	def release(self):
		"""requests object handles this automatically"""
		if hasattr(self, '_pool'):
			self._pool.pool_put(self)

POOL_SIZE=8
class HTTPRequestsResponsePool(ObjectPool):
	def __init__(self, netloc, size=POOL_SIZE):
		super(HTTPRequestsResponsePool, self).__init__(size=size)
		self.netloc = netloc

	def _pool_cleanup(self, resp):
		resp._get_response()
		return True

	@classmethod
	def key(self, full_url):
		p = urlparse(full_url)
		return '%s:%s:%s'%(p.scheme,p.netloc, p.port)

	def _pool_create(self):
		resp = HTTPRequestsResponse()
		resp._pool = self
		return resp

class HTTPRequest(HTTPConnection):

	_pools = {}

	#Avoid certificate verification by default
	verify = False

	def _get_response_object(self):
		pool_key = HTTPRequestsResponsePool.key(self.url)
		try:
			respool = self._pools[pool_key]
		except KeyError:
			self._pools[pool_key] = HTTPRequestsResponsePool(pool_key)
			respool = self._pools[pool_key]
		return respool.pool_get()

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
		http_headers = {}
		for k,v in self.headers.items():
			http_headers[str(k)] = str(v)

		for i,(key, val) in enumerate(self.params.items()):
			param_str = ('?' if i == 0 else '&') + unicode(key) 
			if val is not None:
				param_str+= '='+unicode(val)
			self.url += param_str

		#use pool before request, so that it will block if pool is full
		res = self._get_response_object()
		self._response_object = requests.request(str(self.method),
			str(self.url), headers=http_headers, data=data,
			verify=self.verify, prefetch = False)
		res.request = self._response_object.request
		return res
