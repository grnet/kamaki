# Copyright 2011-2015 GRNET S.A. All rights reserved. #
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

from urllib2 import quote, unquote
from urlparse import urlparse
from threading import Thread
from json import dumps, loads
from time import time
from httplib import ResponseNotReady, HTTPException
from time import sleep
from random import random
import logging
import ssl

from kamaki.clients.utils import https
from kamaki.clients import utils


TIMEOUT = 60.0   # seconds
HTTP_METHODS = ['GET', 'POST', 'PUT', 'HEAD', 'DELETE', 'COPY', 'MOVE']
DEBUGV = logging.DEBUG + 1

logging.addLevelName(DEBUGV, 'DEBUGV')
log = logging.getLogger(__name__)
sendlog = logging.getLogger('%s.send' % __name__)
recvlog = logging.getLogger('%s.recv' % __name__)


def _encode(v):
    if v and isinstance(v, unicode):
        return quote(v.encode('utf-8'))
    return v


class ClientError(Exception):
    def __init__(self, message, status=0, details=None):
        log.debug('ClientError: msg[%s], sts[%s], dtl[%s]' % (
            message, status, details))
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
            self.message = message
            self.status = status if isinstance(status, int) else 0
            self.details = details if details else []

    def __str__(self):
        return self.message


class KamakiSSLError(ClientError):
    """SSL Connection Error"""


class Logged(object):

    LOG_TOKEN = False
    LOG_DATA = False
    LOG_PID = False
    _token = None


class RequestManager(Logged):
    """Handle http request information"""

    def _connection_info(self, url, path, params={}):
        """ Set self.url to scheme://netloc/?params
        :param url: (str or unicode) The service url

        :param path: (str or unicode) The service path (url/path)

        :param params: (dict) Parameters to add to final url

        :returns: (scheme, netloc)
        """
        url = url or 'http://127.0.0.1/'
        url += '' if url.endswith('/') else '/'
        if path:
            url += _encode(path[1:] if path.startswith('/') else path)
        delim = '?'
        for key, val in params.items():
            val = quote('' if val in (None, False) else '%s' % _encode(val))
            url += '%s%s%s' % (delim, key, ('=%s' % val) if val else '')
            delim = '&'
        parsed = urlparse(url)
        self.url = '%s' % url
        self.path = (('%s' % parsed.path) if parsed.path else '/') + (
            '?%s' % parsed.query if parsed.query else '')
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
        self._headers_to_quote, self._header_prefices = [], []

    def dump_log(self):
        plog = ('\t[%s]' % self) if self.LOG_PID else ''
        sendlog.log(DEBUGV, '%s %s://%s%s%s' % (
            self.method, self.scheme, self.netloc, self.path, plog))
        for key, val in self.headers.items():
            if key.lower() in ('x-auth-token', ) and not self.LOG_TOKEN:
                self._token, val = val, '...'
            sendlog.log(DEBUGV, '  %s: %s%s' % (key, val, plog))
        if self.data:
            sendlog.log(DEBUGV, 'data size: %s%s' % (len(self.data), plog))
            if self.LOG_DATA:
                sendlog.log(DEBUGV, utils.escape_ctrl_chars(self.data.replace(
                    self._token, '...') if self._token else self.data))
        else:
            sendlog.log(DEBUGV, 'data size: 0%s' % plog)

    def _encode_headers(self):
        headers = dict()
        for k, v in self.headers.items():
            key = k.lower()
            val = '' if v is None else '%s' % (
                v.encode('utf-8') if isinstance(v, unicode) else v)
            quotable = any([key in self._headers_to_quote, ]) or any(
                [key.startswith(p) for p in self._header_prefices])
            headers[k] = quote(val) if quotable else val
        self.headers = headers

    def perform(self, conn):
        """
        :param conn: (httplib connection object)

        :returns: (HTTPResponse)
        """
        self._encode_headers()
        self.dump_log()
        try:
            conn.request(
                method=self.method.upper(),
                url=self.path.encode('utf-8'),
                headers=self.headers,
                body=self.data)
            sendlog.log(DEBUGV, '')
            keep_trying = TIMEOUT
            while keep_trying > 0:
                try:
                    return conn.getresponse()
                except ResponseNotReady:
                    wait = 0.03 * random()
                    sleep(wait)
                    keep_trying -= wait
        except ssl.SSLError as ssle:
            raise KamakiSSLError('SSL Connection error (%s)' % ssle)
        plog = ('\t[%s]' % self) if self.LOG_PID else ''
        logmsg = 'Kamaki Timeout %s %s%s' % (self.method, self.path, plog)
        recvlog.log(DEBUGV, logmsg)
        raise ClientError('HTTPResponse takes too long - kamaki timeout')

    @property
    def headers_to_quote(self):
        return self._headers_to_quote

    @headers_to_quote.setter
    def headers_to_quote(self, header_keys):
        self._headers_to_quote += [k.lower() for k in header_keys]
        self._headers_to_quote = list(set(self._headers_to_quote))

    @property
    def header_prefices(self):
        return self._header_prefices

    @header_prefices.setter
    def header_prefices(self, header_key_prefices):
        self._header_prefices += [p.lower() for p in header_key_prefices]
        self._header_prefices = list(set(self._header_prefices))


class ResponseManager(Logged):
    """Manage the http request and handle the response data, headers, etc."""

    def __init__(self, request, poolsize=None, connection_retry_limit=0):
        """
        :param request: (RequestManager)

        :param poolsize: (int) the size of the connection pool

        :param connection_retry_limit: (int)
        """
        self.CONNECTION_TRY_LIMIT = 1 + connection_retry_limit
        self.request = request
        self._request_performed = False
        self.poolsize = poolsize
        self._headers_to_decode, self._header_prefices = [], []

    def _get_headers_to_decode(self, headers):
        keys = set([k.lower() for k, v in headers])
        encodable = list(keys.intersection(self.headers_to_decode))

        def has_prefix(s):
            for k in self.header_prefices:
                if s.startswith(k):
                    return True
            return False
        return encodable + filter(has_prefix, keys.difference(encodable))

    def _get_response(self):
        if self._request_performed:
            return

        pool_kw = dict(size=self.poolsize) if self.poolsize else dict()
        for retries in range(1, self.CONNECTION_TRY_LIMIT + 1):
            try:
                with https.PooledHTTPConnection(
                        self.request.netloc, self.request.scheme,
                        **pool_kw) as connection:
                    self.request.LOG_TOKEN = self.LOG_TOKEN
                    self.request.LOG_DATA = self.LOG_DATA
                    self.request.LOG_PID = self.LOG_PID
                    r = self.request.perform(connection)
                    plog = ''
                    if self.LOG_PID:
                        recvlog.log(DEBUGV, '\n%s <-- %s <-- [req: %s]\n' % (
                            self, r, self.request))
                        plog = '\t[%s]' % self
                    self._request_performed = True
                    self._status_code, self._status = r.status, unquote(
                        r.reason)
                    recvlog.log(
                        DEBUGV,
                        '%d %s%s' % (self.status_code, self.status, plog))
                    self._headers = dict()

                    r_headers = r.getheaders()
                    enc_headers = self._get_headers_to_decode(r_headers)
                    for k, v in r_headers:
                        self._headers[k] = unquote(v).decode('utf-8') if (
                            k.lower()) in enc_headers else v
                        recvlog.log(DEBUGV, '  %s: %s%s' % (k, v, plog))
                    self._content = r.read()
                    recvlog.log(DEBUGV, 'data size: %s%s' % (
                        len(self._content) if self._content else 0, plog))
                    if self.LOG_DATA and self._content:
                        data = '%s%s' % (self._content, plog)
                        data = utils.escape_ctrl_chars(data)
                        if self._token:
                            data = data.replace(self._token, '...')
                        recvlog.log(DEBUGV, data)
                break
            except Exception as err:
                if isinstance(err, HTTPException):
                    if retries >= self.CONNECTION_TRY_LIMIT:
                        raise ClientError(
                            'Connection to %s failed %s times (%s: %s )' % (
                                self.request.url, retries, type(err), err))
                else:
                    from traceback import format_stack
                    recvlog.log(
                        DEBUGV, '\n'.join(['%s' % type(err)] + format_stack()))
                    raise

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
    def headers_to_decode(self):
        return self._headers_to_decode

    @headers_to_decode.setter
    def headers_to_decode(self, header_keys):
        self._headers_to_decode += [k.lower() for k in header_keys]
        self._headers_to_decode = list(set(self._headers_to_decode))

    @property
    def header_prefices(self):
        return self._header_prefices

    @header_prefices.setter
    def header_prefices(self, header_key_prefices):
        self._header_prefices += [p.lower() for p in header_key_prefices]
        self._header_prefices = list(set(self._header_prefices))

    @property
    def json(self):
        """
        :returns: (dict) squeezed from json-formated content
        """
        self._get_response()
        try:
            return loads(self._content)
        except ValueError as err:
            raise ClientError('Response not formated in JSON - %s' % err)


class SilentEvent(Thread):
    """Thread-run method(*args, **kwargs)"""
    def __init__(self, method, *args, **kwargs):
        super(self.__class__, self).__init__()
        self.method, self.args, self.kwargs = method, args, kwargs

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
            estatus = e.status if isinstance(e, ClientError) else ''
            recvlog.debug('Thread %s got exception %s\n<%s %s' % (
                self, type(e), estatus, e))
            self._exception = e


class Client(Logged):
    service_type = ''
    MAX_THREADS = 1
    DATE_FORMATS = ['%a %b %d %H:%M:%S %Y', ]
    CONNECTION_RETRY_LIMIT = 0

    def __init__(self, endpoint_url, token, base_url=None):
        #  BW compatibility - keep base_url for some time
        endpoint_url = endpoint_url or base_url
        assert endpoint_url, 'No endpoint_url for client %s' % self
        self.endpoint_url, self.base_url = endpoint_url, endpoint_url
        self.token = token
        self.headers, self.params = dict(), dict()
        self.poolsize = None
        self.request_headers_to_quote = []
        self.request_header_prefices_to_quote = []
        self.response_headers = []
        self.response_header_prefices = []

        # If no CA certificates are set, get the defaults from kamaki.defaults
        if https.HTTPSClientAuthConnection.ca_file is None:
            try:
                from kamaki import defaults
                https.HTTPSClientAuthConnection.ca_file = getattr(
                    defaults, 'CACERTS_DEFAULT_PATH', None)
            except ImportError as ie:
                log.debug('ImportError while loading default certs: %s' % ie)

    @staticmethod
    def _unquote_header_keys(headers, prefices):
        new_keys = dict()
        for k in headers:
            if k.lower().startswith(prefices):
                new_keys[k] = unquote(k).decode('utf-8')
        for old, new in new_keys.items():
            headers[new] = headers.pop(old)

    @staticmethod
    def _quote_header_keys(headers, prefices):
        new_keys = dict()
        for k in headers:
            if k.lower().startswith(prefices):
                new_keys[k] = quote(k.encode('utf-8'))
        for old, new in new_keys.items():
            headers[new] = headers.pop(old)

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

    def async_run(self, method, kwarg_list):
        """Fire threads of operations

        :param method: the method to run in each thread

        :param kwarg_list: (list of dicts) the arguments to pass in each method
            call

        :returns: (list) the results of each method call w.r. to the order of
            kwarg_list
        """
        flying, results = {}, {}
        self._init_thread_limit()
        for index, kwargs in enumerate(kwarg_list):
            self._watch_thread_limit(flying.values())
            flying[index] = SilentEvent(method=method, **kwargs)
            flying[index].start()
            unfinished = {}
            for key, thread in flying.items():
                if thread.isAlive():
                    unfinished[key] = thread
                elif thread.exception:
                    raise thread.exception
                else:
                    results[key] = thread.value
            flying = unfinished
        sendlog.debug('- - - wait for threads to finish')
        for key, thread in flying.items():
            if thread.isAlive():
                thread.join()
            if thread.exception:
                raise thread.exception
            results[key] = thread.value
        return results.values()

    def set_header(self, name, value, iff=True):
        """Set a header 'name':'value'"""
        if value is not None and iff:
            self.headers['%s' % name] = '%s' % value

    def set_param(self, name, value=None, iff=True):
        if iff:
            self.params[name] = '%s' % value

    def request(
            self, method, path,
            async_headers=dict(), async_params=dict(),
            **kwargs):
        """Commit an HTTP request to endpoint_url/path
        Requests are commited to and performed by Request/ResponseManager
        These classes perform a lazy http request. Present method, by default,
        enforces them to perform the http call. Hint: call present method with
        success=None to get a non-performed ResponseManager object.
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
            plog = ('\t[%s]' % self) if self.LOG_PID else ''
            sendlog.log(
                DEBUGV, '\n\nCMT %s@%s%s', method, self.endpoint_url, plog)
            req = RequestManager(
                method, self.endpoint_url, path,
                data=data, headers=headers, params=params)
            req.headers_to_quote = self.request_headers_to_quote
            req.header_prefices = self.request_header_prefices_to_quote
            #  req.log()
            r = ResponseManager(
                req,
                poolsize=self.poolsize,
                connection_retry_limit=self.CONNECTION_RETRY_LIMIT)
            r.headers_to_decode = self.response_headers
            r.header_prefices = self.response_header_prefices
            r.LOG_TOKEN, r.LOG_DATA, r.LOG_PID = (
                self.LOG_TOKEN, self.LOG_DATA, self.LOG_PID)
            r._token = headers['X-Auth-Token']
        finally:
            self.headers = dict()
            self.params = dict()

        if success is not None:
            # Success can either be an int or a collection
            success = (success,) if isinstance(success, int) else success
            if r.status_code not in success:
                log.debug(u'Client caught error %s (%s)' % (r, type(r)))
                status_msg = getattr(r, 'status', '')
                try:
                    message = u'%s %s\n' % (status_msg, r.text)
                except:
                    message = u'%s %s\n' % (status_msg, r)
                status = getattr(r, 'status_code', getattr(r, 'status', 0))
                raise ClientError(message, status=status)
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


def wait(poll, poll_params, stop, delay=1, timeout=100, wait_cb=None):
    """Wait as long as the stop method returns False, polling each round
    :param poll: (method) the polling method is called with poll_params. By
        convention, it returns a dict of information about the item
    :param poll_params: (iterable) each round, call poll with these parameters
    :param stop: (method) gets the results of poll method as input and decides
        if the wait method should stop
    :param delay: (int) how long to wait (in seconds) between polls
    :param timeout: (int) if this number of polls is reached, stop
    :param wait_cb: (method) a call back method that takes item_details as
        input
    :returns: (dict) the last details dict of the item
    """
    results = None
    for polls in range(timeout // delay):
        results = poll(*poll_params)
        if wait_cb:
            wait_cb(results)
        if stop(results):
            break
        sleep(delay)
    return results


class Waiter(object):
    """Use this class to provide blocking API methods - DEPRECATED FROM 0.16"""

    def _wait(
            self, item_id, wait_status, get_status,
            delay=1, max_wait=100, wait_cb=None, wait_until_status=False):
        """DEPRECATED, to be removed in 0.16
        Wait while the item is still in wait_status or to reach it

        :param server_id: integer (str or int)

        :param wait_status: (str)

        :param get_status: (method(self, item_id)) if called, returns
            (status, progress %) If no way to tell progress, return None

        :param delay: time interval between retries

        :param wait_cb: (method(total steps)) returns a generator for
            reporting progress or timeouts i.e., for a progress bar

        :param wait_until_status: (bool) wait FOR (True) or wait WHILE (False)

        :returns: (str) the new mode if successful, (bool) False if timed out
        """
        status, progress = get_status(self, item_id)

        if wait_cb:
            wait_gen = wait_cb(max_wait // delay)
            wait_gen.next()

        if wait_until_status ^ (status != wait_status):
            # if wait_cb:
            #     try:
            #         wait_gen.next()
            #     except Exception:
            #         pass
            return status
        old_wait = total_wait = 0

        while (wait_until_status ^ (status == wait_status)) and (
                total_wait <= max_wait):
            if wait_cb:
                try:
                    for i in range(total_wait - old_wait):
                        wait_gen.next()
                except Exception:
                    break
            old_wait = total_wait
            total_wait = progress or total_wait + 1
            sleep(delay)
            status, progress = get_status(self, item_id)

        if total_wait < max_wait:
            if wait_cb:
                try:
                    for i in range(max_wait):
                        wait_gen.next()
                except:
                    pass
        finished = wait_until_status ^ (status != wait_status)
        return status if finished else False

    def wait_until(
            self, item_id, target_status, get_status,
            delay=1, max_wait=100, wait_cb=None):
        return self._wait(
            item_id, target_status, get_status, delay, max_wait, wait_cb,
            wait_until_status=True)

    def wait_while(
            self, item_id, target_status, get_status,
            delay=1, max_wait=100, wait_cb=None):
        return self._wait(
            item_id, target_status, get_status, delay, max_wait, wait_cb,
            wait_until_status=False)
