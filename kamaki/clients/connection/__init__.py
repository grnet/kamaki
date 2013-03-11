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
    """An abstract HTTP Response object to handle a performed HTTPRequest.
    Subclass implementation required
    """

    def __init__(self, request=None, prefetched=False):
        self.request = request
        self.prefetched = prefetched

    def _get_response(self):
        """Wait for http response as late as possible: the first time needed"""
        if self.prefetched:
            return
        self = self.request.response
        self.prefetched = True

    def release(self):
        """Release the connection.
        """
        raise NotImplementedError

    @property
    def prefetched(self):
        """flag to avoid downloading more than nessecary"""
        return self._prefetched

    @prefetched.setter
    def prefetched(self, p):
        self._prefetched = p

    @property
    def content(self):
        """(binary) request response content (data)"""
        self._get_response()
        return self._content

    @content.setter
    def content(self, v):
        self._content = v

    @property
    def text(self):
        """(str)"""
        self._get_response()
        return self._text

    @text.setter
    def text(self, v):
        self._text = v

    @property
    def json(self):
        """(dict)"""
        self._get_response()
        return self._json

    @json.setter
    def json(self, v):
        self._json = v

    @property
    def headers(self):
        """(dict)"""
        self._get_response()
        return self._headers

    @headers.setter
    def headers(self, v):
        self._headers = v

    @property
    def status_code(self):
        """(int) optional"""
        self._get_response()
        return self._status_code

    @status_code.setter
    def status_code(self, v):
        self._status_code = v

    @property
    def status(self):
        """(str) useful in server error responses"""
        self._get_response()
        return self._status

    @status.setter
    def status(self, v):
        self._status = v

    @property
    def request(self):
        """(HTTPConnection) the source of this response object"""
        return self._request

    @request.setter
    def request(self, v):
        self._request = v


class HTTPConnection(object):
    """An abstract HTTP Connection mechanism. Subclass implementation required
    """

    def __init__(
            self,
            method=None, url=None, params={}, headers={}, poolsize=8):
        self.headers = headers
        self.params = params
        self.url = url
        self.path = ''
        self.method = method
        self.poolsize = poolsize

    @property
    def poolsize(self):
        return self._poolsize

    @poolsize.setter
    def poolsize(self, v):
        assert isinstance(v, (int, long)) and v > 0
        self._poolsize = v

    def set_header(self, name, value):
        self.headers['%s' % name] = '%s' % value

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

    def set_path(self, path):
        self.path = path

    def set_method(self, method):
        self.method = method

    def perform_request(
            self,
            method=None,
            url=None,
            async_headers={},
            async_params={},
            data=None):
        raise NotImplementedError
