# Copyright 2013-2016 GRNET S.A. All rights reserved.
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

from mock import patch, call
from unittest import makeSuite, TestSuite, TextTestRunner, TestCase
from time import sleep
from inspect import getmembers, isclass
from itertools import product
from random import randint

from kamaki.clients.utils.test import Utils
from kamaki.clients.astakos.test import (
    AstakosClient, LoggedAstakosClient, CachedAstakosClient)
from kamaki.clients.compute.test import ComputeClient, ComputeRestClient
from kamaki.clients.network.test import (NetworkClient, NetworkRestClient)
from kamaki.clients.cyclades.test import (
    CycladesComputeClient, CycladesNetworkClient, CycladesBlockStorageClient,
    CycladesComputeRestClient, CycladesBlockStorageRestClient)
from kamaki.clients.image.test import ImageClient
from kamaki.clients.storage.test import StorageClient
from kamaki.clients.pithos.test import (
    PithosClient, PithosRestClient, PithosMethods)
from kamaki.clients.blockstorage.test import (
    BlockStorageRestClient, BlockStorageClient)


class ClientError(TestCase):

    def test___init__(self):
        from kamaki.clients import ClientError
        for msg, status, details, exp_msg, exp_status, exp_details in (
                ('some msg', 42, 0.28, 0, 0, 0),
                ('some msg', 'fail', [], 0, 0, 0),
                ('some msg', 42, 'details on error', 0, 0, 0),
                (
                    '404 {"ExampleError":'
                    ' {"message": "a msg", "code": 42, "details": "dets"}}',
                    404,
                    0,
                    '404 ExampleError (a msg)\n',
                    42,
                    ['dets']),
                (
                    '404 {"ExampleError":'
                    ' {"message": "a msg", "code": 42}}',
                    404,
                    'details on error',
                    '404 ExampleError (a msg)\n',
                    42,
                    0),
                (
                    '404 {"ExampleError":'
                    ' {"details": "Explain your error"}}',
                    404,
                    'details on error',
                    '404 ExampleError',
                    0,
                    ['details on error', 'Explain your error']),
                ('some msg\n', -10, ['details', 'on', 'error'], 0, 0, 0)):
            ce = ClientError(msg, status, details)
            exp_msg = exp_msg or (msg if msg.endswith('\n') else msg + '\n')
            exp_status = exp_status or status
            exp_details = exp_details or details
            self.assertEqual('%s' % ce, exp_msg)
            self.assertEqual(
                exp_status if isinstance(exp_status, int) else 0,
                ce.status)
            self.assertEqual(exp_details, ce.details)


class RequestManager(TestCase):

    def setUp(self):
        from kamaki.clients import RequestManager
        self.RM = RequestManager

    def test___init__(self):
        from kamaki.clients import HTTP_METHODS
        method_values = HTTP_METHODS + [v.lower() for v in HTTP_METHODS]
        for args in product(
                tuple(method_values),
                ('http://www.example.com', 'https://example.com', ''),
                ('/some/path', '/' ''),
                ('Some data', '', None),
                (dict(k1='v1', k2='v2'), dict()),
                (dict(k='v', k2=None, k3='v3'), dict(k=0), dict(k='v'), {})):
            req = self.RM(*args)
            method, url, path, data, headers, params = args
            self.assertEqual(req.method, method.upper())
            for i, (k, v) in enumerate(params.items()):
                path += '%s%s%s' % (
                    '&' if '?' in path or i else '?',
                    k,
                    ('=%s' % v) if v else '')
            self.assertEqual(req.path, path)
            self.assertEqual(req.data, data)
            self.assertEqual(req.headers, headers)
        self.assertRaises(AssertionError, self.RM, 'GOT', '', '', '', {}, {})

    @patch('httplib.HTTPConnection.getresponse')
    @patch('httplib.HTTPConnection.request')
    def test_perform(self, request, getresponse):
        from httplib import HTTPConnection
        self.RM('GET', 'http://example.com', '/').perform(
            HTTPConnection('http', 'example.com'))
        expected = dict(body=None, headers={}, url='/', method='GET')
        request.assert_called_once_with(**expected)
        getresponse.assert_called_once_with()


class FakeResp(object):

    READ = 'something to read'
    HEADERS = dict(k='v', k1='v1', k2='v2')
    reason = 'some reason'
    status = 42
    status_code = 200

    def read(self):
        return self.READ

    def getheaders(self):
        return self.HEADERS.items()


class ResponseManager(TestCase):

    def setUp(self):
        from kamaki.clients import ResponseManager, RequestManager
        from httplib import HTTPConnection
        self.RM = ResponseManager(RequestManager('GET', 'http://ok', '/'))
        self.HTTPC = HTTPConnection

    def tearDown(self):
        FakeResp.READ = 'something to read'

    @patch('kamaki.clients.RequestManager.perform', return_value=FakeResp())
    def test_content(self, perform):
        self.assertEqual(self.RM.content, FakeResp.READ)
        self.assertTrue(isinstance(perform.call_args[0][0], self.HTTPC))

    @patch('kamaki.clients.RequestManager.perform', return_value=FakeResp())
    def test_text(self, perform):
        self.assertEqual(self.RM.text, FakeResp.READ)
        self.assertTrue(isinstance(perform.call_args[0][0], self.HTTPC))

    @patch('kamaki.clients.RequestManager.perform', return_value=FakeResp())
    def test_status(self, perform):
        self.assertEqual(self.RM.status, FakeResp.reason)
        self.assertTrue(isinstance(perform.call_args[0][0], self.HTTPC))

    @patch('kamaki.clients.RequestManager.perform', return_value=FakeResp())
    def test_status_code(self, perform):
        self.assertEqual(self.RM.status_code, FakeResp.status)
        self.assertTrue(isinstance(perform.call_args[0][0], self.HTTPC))

    @patch('kamaki.clients.RequestManager.perform', return_value=FakeResp())
    def test_headers(self, perform):
        self.assertEqual(self.RM.headers, FakeResp.HEADERS)
        self.assertTrue(isinstance(perform.call_args[0][0], self.HTTPC))

    @patch('kamaki.clients.RequestManager.perform', return_value=FakeResp())
    def test_json(self, perform):
        try:
            self.RM.json
        except Exception as e:
            self.assertEqual(
                '%s' % e,
                'Response not formated in JSON - '
                'No JSON object could be decoded\n')

        from json import dumps
        FakeResp.READ = dumps(FakeResp.HEADERS)
        self.RM._request_performed = False
        self.assertEqual(self.RM.json, FakeResp.HEADERS)
        self.assertTrue(isinstance(perform.call_args[0][0], self.HTTPC))

    @patch('kamaki.clients.RequestManager.perform', return_value=FakeResp())
    def test_all(self, perform):
        self.assertEqual(self.RM.content, FakeResp.READ)
        self.assertEqual(self.RM.text, FakeResp.READ)
        self.assertEqual(self.RM.status, FakeResp.reason)
        self.assertEqual(self.RM.status_code, FakeResp.status)
        self.assertEqual(self.RM.headers, FakeResp.HEADERS)
        assert perform.call_count == 1


class SilentEvent(TestCase):

    def thread_content(self, methodid, raiseException=0):
        wait = 0.1
        self.can_finish = -1
        while self.can_finish < methodid and wait < 4:
            sleep(wait)
            wait = 2 * wait
        if raiseException and raiseException == methodid:
            raise Exception('Some exception')
        self._value = methodid
        self.assertTrue(wait < 4)

    def setUp(self):
        from kamaki.clients import SilentEvent
        self.SE = SilentEvent

    def test_run(self):
        threads = [self.SE(self.thread_content, i) for i in range(4)]
        for t in threads:
            t.start()

        for i in range(4):
            if threads[i].is_alive():
                threads[i].join()
                self.assertFalse(threads[i].is_alive())
            self.can_finish = i

    def test_value(self):
        threads = [self.SE(self.thread_content, i) for i in range(4)]
        for t in threads:
            t.start()

        for mid, t in enumerate(threads):
            if t.is_alive():
                self.can_finish = mid
                continue
            self.assertTrue(mid, t.value)

    def test_exception(self):
        threads = [self.SE(self.thread_content, i, (i % 2)) for i in range(4)]
        for t in threads:
            t.start()

        for i, t in enumerate(threads):
            if t.is_alive():
                self.can_finish = i
                continue
            if i % 2:
                self.assertTrue(isinstance(t.exception, Exception))
            else:
                self.assertFalse(t.exception)


class FR(object):
    json = None
    text = None
    headers = dict()
    content = json
    status = None
    status_code = 200


class Client(TestCase):

    def assert_dicts_are_equal(self, d1, d2):
        for k, v in d1.items():
            self.assertTrue(k in d2)
            if isinstance(v, dict):
                self.assert_dicts_are_equal(v, d2[k])
            else:
                self.assertEqual(unicode(v), unicode(d2[k]))

    def setUp(self):
        from kamaki.clients import Client
        from kamaki.clients import ClientError as CE
        self.endpoint_url = 'http://example.com'
        self.token = 's0m370k3n=='
        self.client = Client(self.endpoint_url, self.token)
        self.CE = CE

    def tearDown(self):
        FR.text = None
        FR.status = None
        FR.status_code = 200
        self.client.token = self.token

    def test___init__(self):
        self.assertEqual(self.client.endpoint_url, self.endpoint_url)
        self.assertEqual(self.client.token, self.token)
        self.assert_dicts_are_equal(self.client.headers, {})
        DATE_FORMATS = ['%a %b %d %H:%M:%S %Y']
        self.assertEqual(self.client.DATE_FORMATS, DATE_FORMATS)

    def test__init_thread_limit(self):
        exp = 'Nothing set here'
        for faulty in (-1, 0.5, 'a string', {}):
            self.assertRaises(
                AssertionError,
                self.client._init_thread_limit,
                faulty)
            self.assertEqual(exp, getattr(self.client, '_thread_limit', exp))
            self.assertEqual(exp, getattr(self.client, '_elapsed_old', exp))
            self.assertEqual(exp, getattr(self.client, '_elapsed_new', exp))
        self.client._init_thread_limit(42)
        self.assertEqual(42, self.client._thread_limit)
        self.assertEqual(0.0, self.client._elapsed_old)
        self.assertEqual(0.0, self.client._elapsed_new)

    def test__watch_thread_limit(self):
        waits = (
            dict(args=((0.1, 1), (0.1, 2), (0.2, 1), (0.7, 1), (0.3, 2))),
            dict(args=((1.0 - (i / 10.0), (i + 1)) for i in range(7))),
            dict(max=1, args=tuple([(randint(1, 10) / 3.0, 1), ] * 10)),
            dict(
                limit=5,
                args=tuple([
                    (1.0 + (i / 10.0), (5 - i - 1)) for i in range(4)] + [
                    (2.0, 1), (1.9, 2), (2.0, 1), (2.0, 2)])),
            dict(args=tuple(
                [(1.0 - (i / 10.0), (i + 1)) for i in range(7)] + [
                (0.1, 7), (0.2, 6), (0.4, 5), (0.3, 6), (0.2, 7), (0.1, 7)])),)
        for wait_dict in waits:
            if 'max' in wait_dict:
                self.client.MAX_THREADS = wait_dict['max']
            else:
                self.client.MAX_THREADS = 7
            if 'limit' in wait_dict:
                self.client._init_thread_limit(wait_dict['limit'])
            else:
                self.client._init_thread_limit()
                self.client._watch_thread_limit(list())
                self.assertEqual(1, self.client._thread_limit)
            for wait, exp_limit in wait_dict['args']:
                self.client._elapsed_new = wait
                self.client._watch_thread_limit(list())
                self.assertEqual(exp_limit, self.client._thread_limit)

    @patch('kamaki.clients.Client.set_header')
    def test_set_header(self, SH):
        for name, value, condition in product(
                ('n4m3', '', None),
                ('v41u3', None, 42),
                (True, False, None, 1, '')):
            self.client.set_header(name, value, iff=condition)
            self.assertEqual(
                SH.mock_calls[-1], call(name, value, iff=condition))

    @patch('kamaki.clients.Client.set_param')
    def test_set_param(self, SP):
        for name, value, condition in product(
                ('n4m3', '', None),
                ('v41u3', None, 42),
                (True, False, None, 1, '')):
            self.client.set_param(name, value, iff=condition)
            self.assertEqual(
                SP.mock_calls[-1], call(name, value, iff=condition))

    @patch('kamaki.clients.RequestManager', return_value=FR)
    @patch('kamaki.clients.ResponseManager', return_value=FakeResp())
    @patch('kamaki.clients.ResponseManager.__init__')
    def test_request(self, Requ, RespInit, Resp):
        for args in product(
                ('get', '', dict(method='get')),
                ('/some/path', None, ['some', 'path']),
                (dict(), dict(h1='v1'), dict(h1='v2', h2='v2')),
                (dict(), dict(p1='v1'), dict(p1='v2', p2=None, p3='v3')),
                (dict(), dict(data='some data'), dict(
                    success=400,
                    json=dict(k2='v2', k1='v1')))):
            method, path, kwargs = args[0], args[1], args[-1]
            FakeResp.status_code = kwargs.get('success', 200)
            if not (method and (
                    isinstance(method, str) or isinstance(
                        method, unicode)) and (
                    isinstance(path, str) or isinstance(path, unicode))):
                self.assertRaises(
                    AssertionError, self.client.request, method, path,
                    **kwargs)
                continue
            self.client.request(method, path, **kwargs)
            self.assertEqual(
                RespInit.mock_calls[-1],
                call(FR, connection_retry_limit=0, poolsize=None))

    @patch('kamaki.clients.Client.request', return_value='lala')
    def _test_foo(self, foo, request):
        method = getattr(self.client, foo)
        r = method('path', k='v')
        self.assertEqual(r, 'lala')
        request.assert_called_once_with(foo, 'path', k='v')

    def test_delete(self):
        self._test_foo('delete')

    def test_get(self):
        self._test_foo('get')

    def test_head(self):
        self._test_foo('head')

    def test_post(self):
        self._test_foo('post')

    def test_put(self):
        self._test_foo('put')

    def test_copy(self):
        self._test_foo('copy')

    def test_move(self):
        self._test_foo('move')


#  TestCase auxiliary methods

def runTestCase(cls, test_name, args=[], failure_collector=[]):
    """
    :param cls: (TestCase) a set of Tests

    :param test_name: (str)

    :param args: (list) these are prefixed with test_ and used as params when
        instantiating cls

    :param failure_collector: (list) collects info of test failures

    :returns: (int) total # of run tests
    """
    suite = TestSuite()
    if args:
        suite.addTest(cls('_'.join(['test'] + args)))
    else:
        suite.addTest(makeSuite(cls))
    print('* Test * %s *' % test_name)
    r = TextTestRunner(verbosity=2).run(suite)
    failure_collector += r.errors
    failure_collector += r.failures
    return r.testsRun


def _add_value(foo, value):
    def wrap(self):
        return foo(self, value)
    return wrap


def get_test_classes(module=__import__(__name__), name=''):
    module_stack = [module]
    while module_stack:
        module = module_stack[-1]
        module_stack = module_stack[:-1]
        for objname, obj in getmembers(module):
            if (objname == name or not name):
                if isclass(obj) and objname != 'TestCase' and (
                        issubclass(obj, TestCase)):
                    yield (obj, objname)


def main(argv):
    found = False
    failure_collector = list()
    num_of_tests = 0
    for cls, name in get_test_classes(name=argv[1] if len(argv) > 1 else ''):
        found = True
        num_of_tests += runTestCase(cls, name, argv[2:], failure_collector)
    if not found:
        print('Test "%s" not found' % ' '.join(argv[1:]))
    else:
        for i, failure in enumerate(failure_collector):
            print('Failure %s: ' % (i + 1))
            for field in failure:
                print('\t%s' % field)
        print('\nTotal tests run: %s' % num_of_tests)
        print('Total failures: %s' % len(failure_collector))
        if len(failure_collector):
            from sys import exit
            exit(1)


if __name__ == '__main__':
    from sys import argv
    main(argv)
