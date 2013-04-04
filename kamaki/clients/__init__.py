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

from urllib2 import quote
from urlparse import urlparse
from threading import Thread
from json import dumps, loads
from time import time
from httplib import ResponseNotReady
from time import sleep
from random import random

from objpool.http import PooledHTTPConnection

from kamaki.clients.utils import logger

LOG_TOKEN = False
DEBUG_LOG = logger.get_log_filename()

logger.add_file_logger('clients.send', __name__, filename=DEBUG_LOG)
sendlog = logger.get_logger('clients.send')
sendlog.debug('Logging location: %s' % DEBUG_LOG)

logger.add_file_logger('data.send', __name__, filename=DEBUG_LOG)
datasendlog = logger.get_logger('data.send')

logger.add_file_logger('clients.recv', __name__, filename=DEBUG_LOG)
recvlog = logger.get_logger('clients.recv')

logger.add_file_logger('data.recv', __name__, filename=DEBUG_LOG)
datarecvlog = logger.get_logger('data.recv')

logger.add_file_logger('ClientError', __name__, filename=DEBUG_LOG)
clienterrorlog = logger.get_logger('ClientError')

HTTP_METHODS = ['GET', 'POST', 'PUT', 'HEAD', 'DELETE', 'COPY', 'MOVE']


def _encode(v):
    if v and isinstance(v, unicode):
        return quote(v.encode('utf-8'))
    return v


class ClientError(Exception):
    def __init__(self, message, status=0, details=None):
        clienterrorlog.debug(
            'msg[%s], sts[%s], dtl[%s]' % (message, status, details))
        try:
            message += '' if message and message[-1] == '\n' else '\n'
            serv_stat, sep, new_msg = message.partition('{')
            new_msg = sep + new_msg[:-1 if new_msg.endswith('\n') else 0]
            json_msg = loads(new_msg)
            key = json_msg.keys()[0]
            serv_stat = serv_stat.strip()

            json_msg = json_msg[key]
            message = '%s %s (%s)\n' % (
                serv_stat,
                key,
                json_msg['message']) if (
                    'message' in json_msg) else '%s %s' % (serv_stat, key)
            status = json_msg.get('code', status)
            if 'details' in json_msg:
                if not details:
                    details = []
                if not isinstance(details, list):
                    details = [details]
                if json_msg['details']:
                    details.append(json_msg['details'])
        except Exception:
            pass
        finally:
            while message.endswith('\n\n'):
                message = message[:-1]
            super(ClientError, self).__init__(message)
            self.status = status if isinstance(status, int) else 0
            self.details = details if details else []


class RequestManager(object):
    """Handle http request information"""

    def _connection_info(self, url, path, params={}):
        """ Set self.url to scheme://netloc/?params
        :param url: (str or unicode) The service url

        :param path: (str or unicode) The service path (url/path)

        :param params: (dict) Parameters to add to final url

        :returns: (scheme, netloc)
        """
        url = _encode(url) if url else 'http://127.0.0.1/'
        url += '' if url.endswith('/') else '/'
        if path:
            url += _encode(path[1:] if path.startswith('/') else path)
        delim = '?'
        for key, val in params.items():
            val = _encode(val)
            url += '%s%s%s' % (delim, key, ('=%s' % val) if val else '')
            delim = '&'
        parsed = urlparse(url)
        self.url = url
        self.path = parsed.path or '/'
        if parsed.query:
            self.path += '?%s' % parsed.query
        return (parsed.scheme, parsed.netloc)

    def __init__(
            self, method, url, path,
            data=None, headers={}, params={}):
        method = method.upper()
        assert method in HTTP_METHODS, 'Invalid http method %s' % method
        if headers:
            assert isinstance(headers, dict)
        self.headers = dict(headers)
        self.method, self.data = method, data
        self.scheme, self.netloc = self._connection_info(url, path, params)

    def perform(self, conn):
        """
        :param conn: (httplib connection object)

        :returns: (HTTPResponse)
        """
        #  sendlog.debug(
        #    'RequestManager.perform mthd(%s), url(%s), headrs(%s), bdlen(%s)',
        #    self.method, self.url, self.headers, self.data)
        conn.request(
            method=str(self.method.upper()),
            url=str(self.path),
            headers=self.headers,
            body=self.data)
        while True:
            try:
                return conn.getresponse()
            except ResponseNotReady:
                sleep(0.03 * random())


class ResponseManager(object):
    """Manage the http request and handle the response data, headers, etc."""

    def __init__(self, request, poolsize=None):
        """
        :param request: (RequestManager)
        """
        self.request = request
        self._request_performed = False
        self.poolsize = poolsize

    def _get_response(self):
        if self._request_performed:
            return

        pool_kw = dict(size=self.poolsize) if self.poolsize else dict()
        try:
            with PooledHTTPConnection(
                    self.request.netloc, self.request.scheme,
                    **pool_kw) as connection:
                r = self.request.perform(connection)
                #  recvlog.debug('ResponseManager(%s):' % r)
                self._request_performed = True
                self._headers = dict()
                for k, v in r.getheaders():
                    self.headers[k] = v
                    #  recvlog.debug('\t%s: %s\t(%s)' % (k, v, r))
                self._content = r.read()
                self._status_code = r.status
                self._status = r.reason
        except Exception as err:
            from kamaki.clients import recvlog
            from traceback import format_stack
            recvlog.debug('\n'.join(['%s' % type(err)] + format_stack()))
            raise ClientError(
                'Failed while http-connecting to %s (%s)' % (
                    self.request.url,
                    err),
                1000)

    @property
    def status_code(self):
        self._get_response()
        return self._status_code

    @property
    def status(self):
        self._get_response()
        return self._status

    @property
    def headers(self):
        self._get_response()
        return self._headers

    @property
    def content(self):
        self._get_response()
        return self._content

    @property
    def text(self):
        """
        :returns: (str) content
        """
        self._get_response()
        return '%s' % self._content

    @property
    def json(self):
        """
        :returns: (dict) squeezed from json-formated content
        """
        self._get_response()
        try:
            return loads(self._content)
        except ValueError as err:
            ClientError('Response not formated in JSON - %s' % err)


class SilentEvent(Thread):
    """ Thread-run method(*args, **kwargs)"""
    def __init__(self, method, *args, **kwargs):
        super(self.__class__, self).__init__()
        self.method = method
        self.args = args
        self.kwargs = kwargs

    @property
    def exception(self):
        return getattr(self, '_exception', False)

    @property
    def value(self):
        return getattr(self, '_value', None)

    def run(self):
        try:
            self._value = self.method(*(self.args), **(self.kwargs))
        except Exception as e:
            recvlog.debug('Thread %s got exception %s\n<%s %s' % (
                self,
                type(e),
                e.status if isinstance(e, ClientError) else '',
                e))
            self._exception = e


class Client(object):

    def __init__(self, base_url, token):
        self.base_url = base_url
        self.token = token
        self.headers, self.params = dict(), dict()
        self.DATE_FORMATS = [
            '%a %b %d %H:%M:%S %Y',
            '%A, %d-%b-%y %H:%M:%S GMT',
            '%a, %d %b %Y %H:%M:%S GMT']
        self.MAX_THREADS = 7

    def _init_thread_limit(self, limit=1):
        assert isinstance(limit, int) and limit > 0, 'Thread limit not a +int'
        self._thread_limit = limit
        self._elapsed_old = 0.0
        self._elapsed_new = 0.0

    def _watch_thread_limit(self, threadlist):
        self._thread_limit = getattr(self, '_thread_limit', 1)
        self._elapsed_new = getattr(self, '_elapsed_new', 0.0)
        self._elapsed_old = getattr(self, '_elapsed_old', 0.0)
        recvlog.debug('# running threads: %s' % len(threadlist))
        if self._elapsed_old and self._elapsed_old >= self._elapsed_new and (
                self._thread_limit < self.MAX_THREADS):
            self._thread_limit += 1
        elif self._elapsed_old <= self._elapsed_new and self._thread_limit > 1:
            self._thread_limit -= 1

        self._elapsed_old = self._elapsed_new
        if len(threadlist) >= self._thread_limit:
            self._elapsed_new = 0.0
            for thread in threadlist:
                begin_time = time()
                thread.join()
                self._elapsed_new += time() - begin_time
            self._elapsed_new = self._elapsed_new / len(threadlist)
            return []
        return threadlist

    def _raise_for_status(self, r):
        clienterrorlog.debug('raise err from [%s] of type[%s]' % (r, type(r)))
        status_msg = getattr(r, 'status', None) or ''
        try:
            message = '%s %s\n' % (status_msg, r.text)
        except:
            message = '%s %s\n' % (status_msg, r)
        status = getattr(r, 'status_code', getattr(r, 'status', 0))
        raise ClientError(message, status=status)

    def set_header(self, name, value, iff=True):
        """Set a header 'name':'value'"""
        if value is not None and iff:
            self.headers[name] = value

    def set_param(self, name, value=None, iff=True):
        if iff:
            self.params[name] = value

    def request(
            self, method, path,
            async_headers=dict(), async_params=dict(),
            **kwargs):
        """In threaded/asynchronous requests, headers and params are not safe
        Therefore, the standard self.set_header/param system can be used only
        for headers and params that are common for all requests. All other
        params and headers should passes as
        @param async_headers
        @async_params
        E.g. in most queries the 'X-Auth-Token' header might be the same for
        all, but the 'Range' header might be different from request to request.
        """
        assert isinstance(method, str) or isinstance(method, unicode)
        assert method
        assert isinstance(path, str) or isinstance(path, unicode)
        try:
            headers = dict(self.headers)
            headers.update(async_headers)
            params = dict(self.params)
            params.update(async_params)
            success = kwargs.pop('success', 200)
            data = kwargs.pop('data', None)
            headers.setdefault('X-Auth-Token', self.token)
            if 'json' in kwargs:
                data = dumps(kwargs.pop('json'))
                headers.setdefault('Content-Type', 'application/json')
            if data:
                headers.setdefault('Content-Length', '%s' % len(data))

            req = RequestManager(
                method, self.base_url, path,
                data=data, headers=headers, params=params)
            sendlog.info('commit a %s @ %s\t[%s]', method, self.base_url, self)
            sendlog.info('\tpath: %s\t[%s]', req.path, self)
            for key, val in req.headers.items():
                if (not LOG_TOKEN) and key.lower() == 'x-auth-token':
                    continue
                sendlog.info('\t%s: %s [%s]', key, val, self)
            if data:
                datasendlog.info(data)
            sendlog.info('END HTTP request commit\t[%s]', self)

            r = ResponseManager(req)
            recvlog.info('%d %s', r.status_code, r.status)
            for key, val in r.headers.items():
                if (not LOG_TOKEN) and key.lower() == 'x-auth-token':
                    continue
                recvlog.info('%s: %s', key, val)
            if r.content:
                datarecvlog.info(r.content)
        finally:
            self.headers = dict()
            self.params = dict()

        if success is not None:
            # Success can either be an int or a collection
            success = (success,) if isinstance(success, int) else success
            if r.status_code not in success:
                self._raise_for_status(r)
        return r

    def delete(self, path, **kwargs):
        return self.request('delete', path, **kwargs)

    def get(self, path, **kwargs):
        return self.request('get', path, **kwargs)

    def head(self, path, **kwargs):
        return self.request('head', path, **kwargs)

    def post(self, path, **kwargs):
        return self.request('post', path, **kwargs)

    def put(self, path, **kwargs):
        return self.request('put', path, **kwargs)

    def copy(self, path, **kwargs):
        return self.request('copy', path, **kwargs)

    def move(self, path, **kwargs):
        return self.request('move', path, **kwargs)
