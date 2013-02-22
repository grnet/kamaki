# Copyright 2013 GRNET S.A. All rights reserved.
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

from unittest import TestCase, TestSuite, makeSuite, TextTestRunner
from mock import Mock, patch


class _fakeResponse(object):
    sample = 'sample string'
    getheaders = Mock(return_value={})
    content = Mock(return_value=sample)
    read = Mock(return_value=sample)
    status = Mock(return_value=None)
    status_code = 200
    reason = Mock(return_value=None)
    release = Mock()
    headers = {}


class Client(TestCase):

    def setUp(self):
        from kamaki.clients import Client
        from kamaki.clients.connection.kamakicon import (
            KamakiHTTPConnection)
        self.token = 'F@k3T0k3n'
        self.base_url = 'http://www.example.com'
        self.KC = KamakiHTTPConnection
        self.KR = _fakeResponse
        self.c = Client(self.base_url, self.token, self.KC())

    def test_request(self):
        req = self.c.request
        method = 'GET'
        path = '/online/path'
        with patch.object(self.KC, 'perform_request', return_value=self.KR()):
            r = req(method, path)
            self.assertTrue(isinstance(r, self.KR))
            #  async_headers/params do not persist
            #  TODO: Use a real but mocked KamakiConnection instance
            tmp_headers = dict(h1='v1', h2='v2')
            tmp_params = dict(p1='v1', p2=None)
            r = req(method, path, async_headers=tmp_headers)
            self.assertFalse(self.c.headers)
            r = req(method, path, async_params=tmp_params)


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
