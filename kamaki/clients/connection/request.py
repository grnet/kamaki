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
from . import HTTPResponse
#from requests.auth import AuthBase



class HTTPRequest(HTTPConnection):

    def _request(self, method, path, **kwargs):
        success = kwargs.pop('success', 200)

        data = kwargs.pop('data', None)
        self.headers.setdefault('X-Auth-Token', self.token)#this can go to Client

        if 'json' in kwargs:
            data = json.dumps(kwargs.pop('json'))
            self.headers.setdefault('Content-Type', 'application/json')#this can go to Client
        if data:
            self.headers.setdefault('Content-Length', unicode(len(data)))#this can go to Client

        url = self.url #+ path /// No, we don't need that anymore, let Client handle the addition
        kwargs.setdefault('verify', False)  # Disable certificate verification - But why?
        r = requests.request(method, url, headers=self.headers, data=data, **kwargs)

        #url = self.base_url + path
        """ Logging...
        req = r.request
        sendlog.info('%s %s', req.method, req.url)
        for key, val in req.headers.items():
            sendlog.info('%s: %s', key, val)
        sendlog.info('')
        if req.data:
            sendlog.info('%s', req.data)

        recvlog.info('%d %s', r.status_code, r.status)
        for key, val in r.headers.items():
            recvlog.info('%s: %s', key, val)
        recvlog.info('')
        if r.content:
            recvlog.debug(r.content)
        """

        if success is not None:
            # Success can either be an in or a collection
            success = (success,) if isinstance(success, int) else success
            if r.status_code not in success:
                self.raise_for_status(r)
        return r

	def perform_request(self, method=None, url=None, params=None, headers=None, data=None):
		if method is not None:
			self.method = method
		if url is not None:
			self.url = url
		if params is not None:
			self.params = params
		if headers is not None:
			self.headers = headers

		for i,(key, val) in enumerate(params.items()):
			param_str = ('?' if i == 0 else '&') + unicode(key) 
			if val is not None:
				param_str+= '='+unicode(val)
			self.url += param_str

		r = requests.request(self.method, self.url, headers=self.headers, data=data)
		self.response = HTTPResponse(content = r.content, text = r.text, json = r.json,
			headers = r.headers, status_code=r.status_code)
