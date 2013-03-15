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

from kamaki.clients.astakos.test import Astakos
from kamaki.clients.compute.test import Compute, ComputeRestApi
from kamaki.clients.cyclades.test import Cyclades, CycladesRestApi
from kamaki.clients.image.test import Image
from kamaki.clients.storage.test import Storage
from kamaki.clients.pithos.test import Pithos


class SilentEvent(TestCase):

    can_finish = -1

    def thread_content(self, methodid):
        wait = 0.1
        while self.can_finish < methodid and wait < 4:
            sleep(wait)
            wait = 2 * wait
        self._value = methodid
        self.assertTrue(wait < 4)

    def setUp(self):
        from kamaki.clients import SilentEvent
        self.SE = SilentEvent

    def test_threads(self):
        threads = []
        for i in range(4):
            threads.append(self.SE(self.thread_content, i))

        for t in threads:
            t.start()

        for i in range(4):
            self.assertTrue(threads[i].is_alive())
            self.can_finish = i
            threads[i].join()
            self.assertFalse(threads[i].is_alive())


#  TestCase auxiliary methods

def runTestCase(cls, test_name, args=[]):
    suite = TestSuite()
    if args:
        suite.addTest(cls('_'.join(['test'] + args)))
    else:
        suite.addTest(makeSuite(cls))
    print('* Test * %s *' % test_name)
    TextTestRunner(verbosity=2).run(suite)


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
    for cls, name in get_test_classes(name=argv[1] if len(argv) > 1 else ''):
        found = True
        runTestCase(cls, name, argv[2:])
    if not found:
        print('Test "%s" not found' % ' '.join(argv[1:]))


if __name__ == '__main__':
    from sys import argv
    main(argv)
