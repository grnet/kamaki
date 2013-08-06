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
from inspect import getmembers, isclass
from tempfile import NamedTemporaryFile

from kamaki.cli.command_tree.test import Command, CommandTree
from kamaki.cli.argument.test import (
    Argument, ConfigArgument, RuntimeConfigArgument, FlagArgument,
    ValueArgument, IntArgument, DateArgument, VersionArgument,
    KeyValueArgument, ProgressBarArgument, ArgumentParseManager)


class History(TestCase):

    def setUp(self):
        from kamaki.cli.history import History as HClass
        self.HCLASS = HClass
        self.file = NamedTemporaryFile()

    def tearDown(self):
        self.file.close()

    def test__match(self):
        self.assertRaises(AttributeError, self.HCLASS._match, 'ok', 42)
        self.assertRaises(TypeError, self.HCLASS._match, 2.71, 'ok')
        for args, expected in (
                (('XXX', None), True),
                ((None, None), True),
                (('this line has some terms', 'some terms'), True),
                (('this line has some terms', 'some bad terms'), False),
                (('small line', 'not so small line terms'), False),
                ((['line', 'with', 'some', 'terms'], 'some terms'), True),
                ((['line', 'with', 'some terms'], 'some terms'), False)):
            self.assertEqual(self.HCLASS._match(*args), expected)

    def test_get(self):
        history = self.HCLASS(self.file.name)
        self.assertEqual(history.get(), [])

        sample_history = (
            'kamaki history show\n',
            'kamaki file list\n',
            'kamaki touch pithos:f1\n',
            'kamaki file info pithos:f1\n')
        self.file.write(''.join(sample_history))
        self.file.flush()

        expected = ['%s.  \t%s' % (
            i + 1, event) for i, event in enumerate(sample_history)]
        self.assertEqual(history.get(), expected)
        self.assertEqual(history.get('kamaki'), expected)
        self.assertEqual(history.get('file kamaki'), expected[1::2])
        self.assertEqual(history.get('pithos:f1'), expected[2:])
        self.assertEqual(history.get('touch pithos:f1'), expected[2:3])

        for limit in range(len(sample_history)):
            self.assertEqual(history.get(limit=limit), expected[-limit:])
            self.assertEqual(
                history.get('kamaki', limit=limit), expected[-limit:])

    def test_add(self):
        history = self.HCLASS(self.file.name)
        some_strings = ('a brick', 'two bricks', 'another brick', 'A wall!')
        for i, line in enumerate(some_strings):
            history.add(line)
            self.file.seek(0)
            self.assertEqual(
                self.file.read(), '\n'.join(some_strings[:(i + 1)]) + '\n')

    def test_clean(self):
        content = 'a brick\ntwo bricks\nanother brick\nA wall!\n'
        self.file.write(content)
        self.file.flush()
        self.file.seek(0)
        self.assertEqual(self.file.read(), content)
        history = self.HCLASS(self.file.name)
        history.clean()
        self.file.seek(0)
        self.assertEqual(self.file.read(), '')

    def test_retrieve(self):
        sample_history = (
            'kamaki history show\n',
            'kamaki file list\n',
            'kamaki touch pithos:f1\n',
            'kamaki file info pithos:f1\n',
            'current / last command is always excluded')
        self.file.write(''.join(sample_history))
        self.file.flush()

        history = self.HCLASS(self.file.name)
        self.assertRaises(ValueError, history.retrieve, 'must be number')
        self.assertRaises(TypeError, history.retrieve, [1, 2, 3])

        for i in (0, len(sample_history), -len(sample_history)):
            self.assertEqual(history.retrieve(i), None)
        for i in range(1, len(sample_history)):
            self.assertEqual(history.retrieve(i), sample_history[i - 1])
            self.assertEqual(history.retrieve(- i), sample_history[- i - 1])


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
