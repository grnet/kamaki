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

from unittest import TestCase, TestSuite, TextTestRunner, TestLoader
from mock import Mock


class KamakiResponse(TestCase):

    def setUp(self):
        from kamaki.clients.connection import KamakiResponse as HTTPR
        self.resp = HTTPR('Abstract class, so test with fake request (str)')

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


def main(argv):
    classes = dict(
        KamakiResponse=KamakiResponse,
        KamakiConnection=KamakiConnection)
    if argv:
        field = set(classes.keys()).intersection(argv[:1])
    else:
        field = classes.keys()
    for cls in [classes[item] for item in field]:
        if argv[1:]:
            suite = TestSuite()
            test_method = 'test_%s' % '_'.join(argv[1:])
            suite.addTest(cls(test_method))
        else:
            suite = TestLoader().loadTestsFromTestCase(cls)
        TextTestRunner(verbosity=2).run(suite)


if __name__ == '__main__':
    from sys import argv
    main(argv[1:])
