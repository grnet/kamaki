# Copyright 2013 GRNET S.A. All rights reserved.
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

from unittest import TestCase, TestSuite, makeSuite, TextTestRunner
from mock import Mock, patch, call
from random import randrange
from urllib2 import quote

from kamaki.clients import connection
from kamaki.clients.connection import errors, kamakicon


def _encode(v):
    if v and isinstance(v, unicode):
        return quote(v.encode('utf-8'))
    return v


class KamakiConnection(TestCase):
    v_samples = {'title': 'value', 5: 'value'}
    n_samples = {'title': None, 5: None}
    false_samples = {None: 'value', 0: 'value'}

    def setUp(self):
        from kamaki.clients.connection import KamakiConnection as HTTPC
        self.conn = HTTPC()
        self.conn.reset_headers()
        self.conn.reset_params()

    def test_poolsize(self):

        def set_poolsize(poolsize):
            self.conn.poolsize = poolsize

        from kamaki.clients.connection import KamakiConnection as HTTPC
        for poolsize in ('non integer', -10, 0):
            err = AssertionError
            self.assertRaises(err, set_poolsize, poolsize)
        for poolsize in (1, 100, 1024 * 1024 * 1024 * 1024):
            self.conn.poolsize = poolsize
            self.assertEquals(self.conn.poolsize, poolsize)
            self.assertEquals(HTTPC(poolsize=poolsize).poolsize, poolsize)

    def test_set_header(self):
        cnn = self.conn
        for k, v in self.v_samples.items():
            cnn.set_header(k, v)
            self.assertEquals(cnn.headers[unicode(k)], unicode(v))
        for k, v in self.n_samples.items():
            cnn.set_header(k, v)
            self.assertEquals(cnn.headers[unicode(k)], unicode(v))
        for k, v in self.false_samples.items():
            self.assertRaises(AssertionError, cnn.set_header, k, v)
        self.assertEquals(len(cnn.headers), 2)

    def test_set_param(self):
        cnn = self.conn
        for k, v in self.v_samples.items():
            cnn.set_param(k, v)
            self.assertEquals(cnn.params[unicode(k)], v)
        for k, v in self.n_samples.items():
            cnn.set_param(k, v)
            self.assertEquals(cnn.params[unicode(k)], v)
        for k, v in self.false_samples.items():
            self.assertRaises(AssertionError, cnn.set_param, k, v)
        self.assertEquals(len(cnn.params), 2)

    def test_remove_header(self):
        cnn = self.conn
        for k, v in self.v_samples.items():
            cnn.headers[unicode(k)] = unicode(v)
        for k in self.v_samples:
            cnn.remove_header(k)
            self.assertFalse(k in cnn.headers)

    def test_remove_param(self):
        cnn = self.conn
        for k, v in self.v_samples.items():
            cnn.params[unicode(k)] = unicode(v)
        for k in self.v_samples:
            cnn.remove_param(k)
            self.assertFalse(k in cnn.params)

    def test_replace_headers(self):
        cnn = self.conn
        cnn.headers = self.v_samples
        cnn.replace_headers({1: 'one', 2: 'two'})
        for k in self.v_samples:
            self.assertFalse(k in cnn.headers)

    def test_replace_params(self):
        cnn = self.conn
        cnn.params = self.v_samples
        cnn.replace_params({1: 'one', 2: 'two'})
        for k in self.v_samples:
            self.assertFalse(k in cnn.params)

    def test_reset_headers(self):
        cnn = self.conn
        cnn.headers = self.v_samples
        cnn.reset_headers()
        self.assertFalse(cnn.headers)

    def test_reset_params(self):
        cnn = self.conn
        cnn.params = self.v_samples
        cnn.reset_params()
        self.assertFalse(cnn.params)

    def test_set_url(self):
        self.assertFalse(self.conn.url)
        sample_url = 'http://example.com'
        self.conn.set_url(sample_url)
        self.assertEquals(self.conn.url, sample_url)

    def test_set_path(self):
        self.assertFalse(self.conn.path)
        sample_path = '/example/local/path'
        self.conn.set_path(sample_path)
        self.assertEquals(self.conn.path, sample_path)

    def test_set_method(self):
        self.assertFalse(self.conn.method)
        sample_method = 'GET'
        self.conn.set_method(sample_method)
        self.assertEquals(self.conn.method, sample_method)

    def test_perform_request(self):
        self.assertRaises(NotImplementedError, self.conn.perform_request)


class KamakiHTTPConnection(TestCase):

    def setUp(self):
        self.conn = kamakicon.KamakiHTTPConnection()
        self.conn.reset_params()
        self.conn.reset_headers()

    def test__retrieve_connection_info(self):
        async_params = dict(param1='val1', param2=None, param3=42)
        r = self.conn._retrieve_connection_info(async_params)
        self.assertEquals(r, ('http', '127.0.0.1'))
        expected = '?%s' % '&'.join([(
            '%s=%s' % (k, v)) if v else (
            '%s' % k) for k, v in async_params.items()])
        self.assertEquals('http://127.0.0.1%s' % expected, self.conn.url)

        for schnet in (
            ('http', 'www.example.com'), ('https', 'www.example.com'),
            ('ftp', 'www.example.com'), ('ftps', 'www.example.com'),
            ('http', 'www.example.com/v1'), ('https', 'www.example.com/v1')):
            self.conn = kamakicon.KamakiHTTPConnection(url='%s://%s' % schnet)
            self.conn.url = '%s://%s' % schnet
            r = self.conn._retrieve_connection_info(async_params)
            if schnet[1].endswith('v1'):
                self.assertEquals(r, (schnet[0], schnet[1][:-3]))
            else:
                self.assertEquals(r, schnet)
            self.assertEquals(
                '%s://%s/%s' % (schnet[0], schnet[1], expected),
                self.conn.url)

    def test_perform_request(self):
        from httplib import HTTPConnection
        from objpool import http
        pr = self.conn.perform_request
        kwargs = dict(
            data='',
            method='GET',
            async_headers=dict(),
            async_params=dict())
        utf_test = u'\u03a6\u03bf\u03cd\u03c4\u03c3\u03bf\u03c2'
        utf_dict = dict(utf=utf_test)
        ascii_dict = dict(ascii1='myAscii', ascii2=None)
        kwargs0 = dict(
            data='',
            method='get',
            async_headers=utf_dict,
            async_params=ascii_dict)

        def get_expected():
            expected = []
            for k, v in kwargs0['async_params'].items():
                v = _encode(v)
                expected.append(('%s=%s' % (k, v)) if v else ('%s' % k))
            return '&'.join(expected)

        KCError = errors.KamakiConnectionError
        fakecon = HTTPConnection('X', 'Y')

        with patch.object(http, 'get_http_connection', return_value=fakecon):
            with patch.object(HTTPConnection, 'request') as request:
                r = pr(**kwargs)
                self.assertTrue(isinstance(r, kamakicon.KamakiHTTPResponse))
                self.assertEquals(
                    request.mock_calls[-1],
                    call(body='', headers={}, url='/', method='GET'))

                pr(**kwargs0)

                exp_headers = dict(kwargs0['async_headers'])
                exp_headers['utf'] = _encode(exp_headers['utf'])

                self.assertEquals(
                    request.mock_calls[-1],
                    call(
                        body=kwargs0['data'],
                        headers=exp_headers,
                        url='/?%s' % get_expected(),
                        method=kwargs0['method'].upper()))

                self.conn = kamakicon.KamakiHTTPConnection()
                (kwargs0['async_params'], kwargs0['async_headers']) = (
                    kwargs0['async_headers'], kwargs0['async_params'])
                kwargs0['async_headers']['ascii2'] = 'None'
                self.conn.perform_request(**kwargs0)
                self.assertEquals(
                    request.mock_calls[-1],
                    call(
                        body=kwargs0['data'],
                        headers=kwargs0['async_headers'],
                        url='/?%s' % get_expected(),
                        method=kwargs0['method'].upper()))

            err = IOError('IO Error')
            with patch.object(HTTPConnection, 'request', side_effect=err):
                self.assertRaises(KCError, pr, **kwargs)

        err = ValueError('Cannot Establish connection')
        with patch.object(http, 'get_http_connection', side_effect=err):
            self.assertRaises(KCError, pr, **kwargs)

        err = Exception('Any other error')
        with patch.object(http, 'get_http_connection', side_effect=err):
            self.assertRaises(KCError, pr, **kwargs)


class KamakiHTTPResponse(TestCase):

    class fakeResponse(object):
        sample = 'sample string'
        getheaders = Mock(return_value={})
        read = Mock(return_value=sample)
        status = Mock(return_value=None)
        reason = Mock(return_value=None)

    def setUp(self):
        from httplib import HTTPConnection
        self.HTC = HTTPConnection
        self.FR = self.fakeResponse

    def test_text(self):
        with patch.object(self.HTC, 'getresponse', return_value=self.FR()):
            self.resp = kamakicon.KamakiHTTPResponse(self.HTC('X', 'Y'))
            self.assertEquals(self.resp.text, self.FR.sample)
            sample2 = 'some other string'
            self.resp.text = sample2
            self.assertNotEquals(self.resp.text, sample2)

    def test_json(self):
        with patch.object(self.HTC, 'getresponse', return_value=self.FR()):
            self.resp = kamakicon.KamakiHTTPResponse(self.HTC('X', 'Y'))
            self.assertRaises(errors.KamakiResponseError, self.resp.json)
            sample2 = '{"antoher":"sample", "formated":"in_json"}'
            with patch.object(self.FR, 'read', return_value=sample2):
                self.resp = kamakicon.KamakiHTTPResponse(self.HTC('X', 'Y'))
                from json import loads
                self.assertEquals(loads(sample2), self.resp.json)

    def test_pool_lock(self):
        exceptions_left = 100
        while exceptions_left:
            kre = errors.KamakiResponseError
            with patch.object(self.HTC, 'close', return_value=True):
                self.resp = kamakicon.KamakiHTTPResponse(self.HTC('X', 'Y'))
                if randrange(10):
                    with patch.object(
                            self.HTC,
                            'getresponse',
                            return_value=self.FR()):
                        self.assertEquals(self.resp.text, self.FR.sample)
                else:
                    with patch.object(
                            self.HTC,
                            'getresponse',
                            side_effect=kre('A random error')):
                        try:
                            self.resp.text
                        except kre:
                            exceptions_left -= 1
                        else:
                            self.assertTrue(False)
                self.HTC.close.assert_called_with()


class KamakiResponse(TestCase):

    def setUp(self):
        self.resp = connection.KamakiResponse(
            'Abstract class, so test with fake request (str)')

    def _mock_get_response(foo):
        def mocker(self):
            self.resp._get_response = Mock()
            foo(self)
        return mocker

    def test_release(self):
        self.assertRaises(NotImplementedError, self.resp.release)

    def test_prefetched(self):
        self.assertFalse(self.resp.prefetched)
        self.resp.prefetched = True
        self.assertTrue(self.resp.prefetched)

    @_mock_get_response
    def test_content(self):
        rsp = self.resp
        for cont in ('Sample Content', u'\u03c7\u03cd\u03bd\u03c9\x00'):
            rsp.content = cont
            self.assertEquals(rsp.content, cont)

    (
        test_text,
        test_json,
        test_headers,
        test_status,
        test_status_code) = 5 * (test_content,)

    def test_request(self):
        r = self.resp.request
        self.assertTrue(isinstance(r, str))


def get_test_classes(module=__import__(__name__), name=''):
    from inspect import getmembers, isclass
    for objname, obj in getmembers(module):
        if (objname == name or not name) and isclass(obj) and (
                issubclass(obj, TestCase)):
            yield (obj, objname)


def main(argv):
    for cls, name in get_test_classes(name=argv[1] if len(argv) > 1 else ''):
        args = argv[2:]
        suite = TestSuite()
        if args:
            suite.addTest(cls('_'.join(['test'] + args)))
        else:
            suite.addTest(makeSuite(cls))
        print('Test %s' % name)
        TextTestRunner(verbosity=2).run(suite)


if __name__ == '__main__':
    from sys import argv
    main(argv)
