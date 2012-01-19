# Copyright 2011 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or
# without modification, are permitted provided that the following
# conditions are met:
#
#   1. Redistributions of source code must retain the above
#      copyright notice, this list of conditions and the following
#      disclaimer.
#
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
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

import json
import logging

from httplib import HTTPConnection, HTTPSConnection
from urlparse import urlparse

from . import ClientError


log = logging.getLogger('kamaki.clients')


class HTTPClient(object):
    def __init__(self, config):
        self.config = config
    
    @property
    def url(self):
        url = self.config.get('url')
        if not url:
            raise ClientError('No URL was given')
        return url
    
    @property
    def token(self):
        token = self.config.get('token')
        if not token:
            raise ClientError('No token was given')
        return token
    
    def raw_http_cmd(self, method, path, body=None, headers=None, success=200,
                     json_reply=False):
        p = urlparse(self.url)
        path = p.path + path
        if p.scheme == 'http':
            conn = HTTPConnection(p.netloc)
        elif p.scheme == 'https':
            conn = HTTPSConnection(p.netloc)
        else:
            raise ClientError('Unknown URL scheme')
        
        headers = headers or {}
        headers['X-Auth-Token'] = self.token
        if body:
            headers.setdefault('Content-Type', 'application/json')
            headers['Content-Length'] = len(body)
        
        log.debug('>' * 50)
        log.debug('%s %s', method, path)
        for key, val in headers.items():
            log.debug('%s: %s', key, val)
        if body:
            log.debug('')
            log.debug(body)
        
        conn.request(method, path, body, headers)
        
        resp = conn.getresponse()
        reply = resp.read()
        
        log.debug('<' * 50)
        log.info('%d %s', resp.status, resp.reason)
        for key, val in resp.getheaders():
            log.info('%s: %s', key.capitalize(), val)
        log.info('')
        log.debug(reply)
        log.debug('-' * 50)
        
        if json_reply:
            try:
                reply = json.loads(reply) if reply else {}
            except ValueError:
                raise ClientError('Did not receive valid JSON reply',
                                  resp.status, reply)
        
        if success and resp.status != success:
            if len(reply) == 1:
                if json_reply:
                    key = reply.keys()[0]
                    val = reply[key]
                    message = '%s: %s' % (key, val.get('message', ''))
                    details = val.get('details', '')
                else:
                    message = reply
                    details = ''
    
                raise ClientError(message, resp.status, details)
            else:
                raise ClientError('Invalid response from the server')
        
        return resp, reply
    
    def http_cmd(self, method, path, body=None, headers=None, success=200):
        resp, reply = self.raw_http_cmd(method, path, body, headers, success,
                                        json_reply=True)
        return reply
    
    def http_get(self, path, success=200):
        return self.http_cmd('GET', path, success=success)
    
    def http_post(self, path, body=None, headers=None, success=202):
        return self.http_cmd('POST', path, body, headers, success)
    
    def http_put(self, path, body=None, headers=None, success=204):
        return self.http_cmd('PUT', path, body, headers, success)
    
    def http_delete(self, path, success=204):
        return self.http_cmd('DELETE', path, success=success)
