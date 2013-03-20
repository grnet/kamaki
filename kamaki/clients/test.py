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

from unittest import makeSuite, TestSuite, TextTestRunner, TestCase
from time import sleep
from inspect import getmembers, isclass
from json import loads

from kamaki.clients.connection.test import (
    KamakiConnection,
    KamakiHTTPConnection,
    KamakiResponse,
    KamakiHTTPResponse)
from kamaki.clients.utils.test import Utils
from kamaki.clients.astakos.test import Astakos
from kamaki.clients.compute.test import Compute, ComputeRest
from kamaki.clients.cyclades.test import Cyclades, CycladesRest
from kamaki.clients.image.test import Image
from kamaki.clients.storage.test import Storage
from kamaki.clients.pithos.test import Pithos, PithosRest


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
            self.assertTrue(threads[i].is_alive())
            self.can_finish = i
            threads[i].join()
            self.assertFalse(threads[i].is_alive())

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


class FakeConnection(object):
    """A fake Connection class"""

    def __init__(self):
        pass


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
        self.base_url = 'http://example.com'
        self.token = 's0m370k3n=='
        self.client = Client(self.base_url, self.token, FakeConnection())

    def test___init__(self):
        self.assertEqual(self.client.base_url, self.base_url)
        self.assertEqual(self.client.token, self.token)
        self.assert_dicts_are_equal(self.client.headers, {})
        DATE_FORMATS = [
            '%a %b %d %H:%M:%S %Y',
            '%A, %d-%b-%y %H:%M:%S GMT',
            '%a, %d %b %Y %H:%M:%S GMT']
        self.assertEqual(self.client.DATE_FORMATS, DATE_FORMATS)
        self.assertTrue(isinstance(self.client.http_client, FakeConnection))


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


if __name__ == '__main__':
    from sys import argv
    main(argv)
