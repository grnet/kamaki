# Copyright 2011 GRNET S.A. All rights reserved.
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

import unittest

from kamaki import utils
from kamaki import cli

class testUtils(unittest.TestCase):
    def setUp(self):
        self.sampleDict0 = {'string @1st level':'yes', 'dict @1st level':{'string @2nd level':'ok', 2:['parent is a number, but I am a string', 1, '_2_', 3, 4, 5, {'string @3nd level descibing the dict':'I am in a dict in a list in a dict', 'number @3nd level':42}, 6, 7]}, 'empty dict @1st level':{}, 'empty list @1st level':[]}
        self.sampleList0 = ['dict @ list level 2 follows', self.sampleDict0]
        self.sampleList0 = ['list @ list level 1 follows', self.sampleList0, 'dict at list level 1 follows', self.sampleDict0]
    def test_print_dict(self):
        print('\nCheck this by yourself... Fields are autodesciptive')
        utils.print_dict(self.sampleDict0)
    def test_print_list(self):
        print('\nCheck this by yourself... Fields are autodesciptive')
        utils.print_list(self.sampleList0)
    def test_print_item(self):
        print('\nShould print the dict of print_dict test...')
        utils.print_items(self.sampleList0, title=('dict at list level 1 follows', 'whatever'))
    def test_format_size(self):
        self.assertEqual('1B', utils.format_size(1))
        self.assertEqual('512B', utils.format_size(512))
        self.assertEqual('1K', utils.format_size(1024))
        self.assertEqual('3.9K', utils.format_size(4000))
        self.assertEqual('97.7K', utils.format_size(100000))
        self.assertEqual('488.8M', utils.format_size(512512512))
        self.assertEqual('105.6G', utils.format_size(113416789123))
        self.assertEqual('115G', utils.format_size(123456789123))
        self.assertEqual('1.1T', utils.format_size(1234567891233))

class testCLI(unittest.TestCase):

    def setUp(self):
        pass

    def _test_server_instance(self, i):
        self.assertEqual('compute', i.api)
        self.assertEqual('server', i.group)
    def test_server_list(self):
        cl = cli.server_list()
        self._test_server_instance(cl)
        self.assertEqual('list', cl.name)
    def test_server_info(self):
        cl = cli.server_info()
        self._test_server_instance(cl)
        self.assertEqual('info', cl.name)

def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(testUtils))
    suite.addTest(unittest.makeSuite(testCLI))
    return suite

if __name__ == '__main__':
    suiteFew = unittest.TestSuite()

    #kamaki/utils.py
    suiteFew.addTest(testUtils('test_print_dict'))
    suiteFew.addTest(testUtils('test_print_list'))
    suiteFew.addTest(testUtils('test_print_item'))
    suiteFew.addTest(testUtils('test_format_size'))

    #kamaki/cli.py
    suiteFew.addTest(testCLI('test_server_list'))
    suiteFew.addTest(testCLI('test_server_info'))

    unittest.TextTestRunner(verbosity = 2).run(suite())
