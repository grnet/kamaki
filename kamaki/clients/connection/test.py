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


class HTTPResponse(TestCase):

    def setUp(self):
        from kamaki.clients.connection import HTTPResponse as HTTPR
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
        from httplib import HTTPSConnection
        r = self.resp.request
        self.assertTrue(isinstance(r, HTTPSConnection))


def main(argv):
    if argv:
        suite = TestSuite()
        test_method = 'test_%s' % '_'.join(argv)
        suite.addTest(HTTPResponse(test_method))
    else:
        suite = TestLoader().loadTestsFromTestCase(HTTPResponse)
    TextTestRunner(verbosity=2).run(suite)


if __name__ == '__main__':
    from sys import argv
    main(argv[1:])
