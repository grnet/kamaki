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
from mock import Mock, patch
from random import randrange

from kamaki.clients import connection
from kamaki.clients.connection import errors, kamakicon


class KamakiConnection(TestCase):
    v_samples = {'title': 'value', 5: 'value'}
    n_samples = {'title': None, 5: None}
    false_samples = {None: 'value', 0: 'value'}

    def setUp(self):
        from kamaki.clients.connection import KamakiConnection as HTTPC
        self.conn = HTTPC()

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

    def test_perform_request(self):
        from httplib import HTTPConnection
        from objpool import http
        pr = self.conn.perform_request
        kwargs = dict(
            data='',
            method='GET',
            async_headers=dict(),
            async_params=dict())

        KCError = errors.KamakiConnectionError
        fakecon = HTTPConnection('X', 'Y')

        with patch.object(http, 'get_http_connection', return_value=fakecon):
            with patch.object(HTTPConnection, 'request', return_value=None):
                r = pr(**kwargs)
                self.assertTrue(isinstance(r, kamakicon.KamakiHTTPResponse))

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
