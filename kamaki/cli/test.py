# Copyright 2013-2014 GRNET S.A. All rights reserved.
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
from mock import patch, call
from itertools import product


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

    def test_add(self):
        history = self.HCLASS(self.file.name)
        some_strings = ('a brick', 'two bricks', 'another brick', 'A wall!')
        for i, line in enumerate(some_strings):
            history.add(line)
            self.file.seek(0)
            self.assertEqual(
                self.file.read(), '\n'.join(some_strings[:(i + 1)]) + '\n')

    def test_empty(self):
        content = 'a brick\ntwo bricks\nanother brick\nA wall!\n'
        self.file.write(content)
        self.file.flush()
        self.file.seek(0)
        self.assertEqual(self.file.read(), content)
        history = self.HCLASS(self.file.name)
        history.empty()
        self.file.seek(0)
        self.assertEqual(self.file.read(), '0\n')

    def test_retrieve(self):
        sample_history = (
            '0\n',
            'kamaki history show\n',
            'kamaki file list\n',
            'kamaki file create /pithos/f1\n',
            'kamaki file info /pithos/f1\n',
            'last command is always excluded')
        self.file.write(''.join(sample_history))
        self.file.flush()

        history = self.HCLASS(self.file.name)
        self.assertRaises(ValueError, history.retrieve, 'must be number')
        self.assertRaises(TypeError, history.retrieve, [1, 2, 3])

        for i in (0, len(sample_history) + 1, - len(sample_history) - 1):
            self.assertEqual(history.retrieve(i), None)
        for i in range(1, len(sample_history)):
            self.assertEqual(history.retrieve(i), sample_history[i])
            self.assertEqual(history.retrieve(- i), sample_history[- i])

    def test_limit(self):
        sample_history = (
            '0\n',
            'kamaki history show\n',
            'kamaki file list\n',
            'kamaki file create /pithos/f1\n',
            'kamaki file info /pithos/f1\n',
            'last command is always excluded')
        sample_len = len(sample_history)
        self.file.write(''.join(sample_history))
        self.file.flush()
        history = self.HCLASS(self.file.name)

        for value, exp_e in (
                    (-2, ValueError),
                    ('non int', ValueError),
                    (None, TypeError)):
            try:
                history.limit = value
            except Exception as e:
                self.assertTrue(isinstance(e, exp_e))

        history.limit = 10
        self.assertEqual(history.limit, 10)
        self.file.seek(0)
        self.assertEqual(len(self.file.readlines()), sample_len)

        history.limit = sample_len - 1
        self.assertEqual(history.limit, sample_len - 1)
        self.file.seek(0)
        self.assertEqual(len(self.file.readlines()), sample_len)


class LoggerMethods(TestCase):

    class PseudoLogger(object):
        level = 'some level'
        _setLevel_calls = []
        _addHandler_calls = []

        def setLevel(self, *args):
            self._setLevel_calls.append(args)

        def addHandler(self, *args):
            self._addHandler_calls.append(args)

    class PseudoHandler(object):
        _setFormatter_calls = []

        def setFormatter(self, *args):
            self._setFormatter_calls.append(args)

    def setUp(self):
        from kamaki.cli.logger import LOG_FILE, _blacklist
        self.LF, self.BL = list(LOG_FILE), dict(_blacklist)

    def tearDown(self):
        self.PseudoLogger._setLevel_calls = []
        self.PseudoLogger._addHandler_calls = []
        self.PseudoLogger._setFormatter_calls = []
        from kamaki.cli.logger import LOG_FILE, _blacklist
        for e in LOG_FILE:
            LOG_FILE.pop()
        for e in self.LF:
            LOG_FILE.append(e)
        _blacklist.clear()
        _blacklist.update(self.BL)

    @patch('kamaki.cli.logger.logging.getLogger', return_value=PseudoLogger())
    def test_deactivate(self, GL):
        from kamaki.cli.logger import deactivate, _blacklist
        self.assertEqual(_blacklist, {})
        deactivate('some logger')
        GL.assert_called_once_with('some logger')
        self.assertEqual(
            _blacklist.get('some logger', None), self.PseudoLogger.level)
        from logging import CRITICAL
        self.assertEqual(self.PseudoLogger._setLevel_calls[-1], (CRITICAL, ))

    @patch('kamaki.cli.logger.logging.getLogger', return_value=PseudoLogger())
    def test_activate(self, GL):
        from kamaki.cli.logger import activate
        activate('another logger')
        GL.assert_called_once_with('another logger')
        self.assertEqual(
            self.PseudoLogger._setLevel_calls[-1], (self.PseudoLogger.level, ))

    def test_get_log_filename(self):
        from kamaki.cli.logger import get_log_filename, LOG_FILE
        f = NamedTemporaryFile()
        for e in LOG_FILE:
            LOG_FILE.pop()
        LOG_FILE.append(f.name)
        self.assertEqual(get_log_filename(), f.name)
        LOG_FILE.pop()
        LOG_FILE.append(2 * f.name)
        print('\n  Should print error msg here: ')
        self.assertEqual(get_log_filename(), None)

    def test_set_log_filename(self):
        from kamaki.cli.logger import set_log_filename, LOG_FILE
        for n in ('some name', 'some other name'):
            set_log_filename(n)
            self.assertEqual(LOG_FILE[0], n)

    @patch('kamaki.cli.logger.get_logger', return_value=PseudoLogger())
    @patch('kamaki.cli.logger.logging.Formatter', return_value='f0rm4t')
    @patch(
        'kamaki.cli.logger.logging.StreamHandler',
        return_value=PseudoHandler())
    @patch(
        'kamaki.cli.logger.logging.FileHandler',
        return_value=PseudoHandler())
    def test__add_logger(self, FH, SH, F, GL):
        from kamaki.cli.logger import _add_logger
        from logging import DEBUG
        stdf, cnt = '%(name)s\n %(message)s', 0
        for name, level, filename, fmt in product(
                ('my logger', ),
                ('my level', None),
                ('my filename', None),
                ('my fmt', None)):
            log = _add_logger(name, level, filename, fmt)
            self.assertTrue(isinstance(log, self.PseudoLogger))
            self.assertEqual(GL.mock_calls[-1], call(name))
            if filename:
                self.assertEqual(FH.mock_calls[-1], call(filename))
            else:
                self.assertEqual(SH.mock_calls[-1], call())
            self.assertEqual(F.mock_calls[-1], call(fmt or stdf))
            self.assertEqual(
                self.PseudoHandler._setFormatter_calls[-1], ('f0rm4t', ))
            cnt += 1
            self.assertEqual(len(self.PseudoLogger._addHandler_calls), cnt)
            h = self.PseudoLogger._addHandler_calls[-1]
            self.assertTrue(isinstance(h[0], self.PseudoHandler))
            l = self.PseudoLogger._setLevel_calls[-1]
            self.assertEqual(l, (level or DEBUG, ))

    @patch('kamaki.cli.logger.get_log_filename', return_value='my log fname')
    @patch('kamaki.cli.logger.get_logger', return_value='my get logger ret')
    def test_add_file_logger(self, GL, GLF):
        from kamaki.cli.logger import add_file_logger
        with patch('kamaki.cli.logger._add_logger', return_value='AL') as AL:
            GLFcount = GLF.call_count
            for name, level, filename in product(
                    ('my name'), ('my level', None), ('my filename', None)):
                self.assertEqual(add_file_logger(name, level, filename), 'AL')
                from logging import DEBUG as dbg
                fmt = '%(name)s(%(levelname)s) %(asctime)s\n\t%(message)s' if (
                    level == dbg) else '%(name)s: %(message)s'
                self.assertEqual(AL.mock_calls[-1], call(
                    name, level, filename or 'my log fname',
                    fmt=fmt))
                if filename:
                    self.assertEqual(GLFcount, GLF.call_count)
                else:
                    GLFcount = GLF.call_count
                    self.assertEqual(GLF.mock_calls[-1], call())
        with patch('kamaki.cli.logger._add_logger', side_effect=Exception):
            self.assertEqual(add_file_logger('X'), 'my get logger ret')
            GL.assert_called_once_with('X')

    @patch('kamaki.cli.logger.get_logger', return_value='my get logger ret')
    def test_add_stream_logger(self, GL):
        from kamaki.cli.logger import add_stream_logger
        with patch('kamaki.cli.logger._add_logger', return_value='AL') as AL:
            for name, level, fmt in product(
                    ('my name'), ('my level', None), ('my fmt', None)):
                self.assertEqual(add_stream_logger(name, level, fmt), 'AL')
                self.assertEqual(AL.mock_calls[-1], call(name, level, fmt=fmt))
        with patch('kamaki.cli.logger._add_logger', side_effect=Exception):
            self.assertEqual(add_stream_logger('X'), 'my get logger ret')
            GL.assert_called_once_with('X')

    @patch('kamaki.cli.logger.logging.getLogger', return_value=PseudoLogger())
    def test_get_logger(self, GL):
        from kamaki.cli.logger import get_logger
        get_logger('my logger name')
        GL.assert_called_once_with('my logger name')


_RET = None


class PseudoException(object):

    def __init__(self, *args):
        global _RET
        _RET = args


class CLIError(TestCase):

    @patch('__builtin__.super', return_value=PseudoException())
    def test___init__(self, S):
        from kamaki.cli.errors import CLIError
        global _RET
        for message, details, importance in (
                ('some msg', [], 0),
                ('some msg\n', 'details', 0),
                ('some msg', ['details1', 'details2'], 10)):
            clie = CLIError(message, details, importance)
            self.assertEqual(S.mock_calls[-1], call(CLIError, clie))
            self.assertEqual(_RET[0], (message + '\n') if (
                message and not message.endswith('\n')) else message)
            self.assertEqual(clie.details, (list(details) if (
                isinstance(details, list)) else ['%s' % details]) if (
                    details) else [])
            self.assertEqual(clie.importance, int(importance))
        clie = CLIError(message, details, 'non int')
        self.assertEqual(clie.importance, 0)

    def test_raiseCLIError(self):
        from kamaki.cli.errors import raiseCLIError, CLIError
        for err, message, importance, details in (
                (Exception('msg'), '', 0, []),
                (Exception('msg'), 'orther msg', 0, []),
                (Exception('msg'), 'orther msg', 0, ['d1', 'd2']),
                (Exception('msg'), '', 10, []),
                (Exception('msg'), '', None, []),
                (CLIError('some msg'), '', None, ['d1', 'd2'])
            ):
            try:
                raiseCLIError(err, message, importance, details)
            except CLIError as clie:
                exp_msg = '%s' % (message or err)
                exp_msg += '' if exp_msg.endswith('\n') else '\n'
                self.assertEqual('%s' % clie, exp_msg)
                self.assertEqual(clie.importance, importance or 0)
                exp_d = list(details) if isinstance(details, list) else [
                    '%s' % (details or '')]
                base_msg = '%s' % err
                if message and base_msg != message:
                    exp_d.append(base_msg)
                self.assertEqual(clie.details, exp_d)


class CLIUnimplemented(TestCase):

    def test___init__(self):
        from kamaki.cli.errors import CLIUnimplemented
        cliu = CLIUnimplemented()
        self.assertEqual(
            '%s' % cliu,
            'I \'M SORRY, DAVE.\nI \'M AFRAID I CAN\'T DO THAT.\n')
        self.assertEqual(cliu.details, [
            '      _        |',
            '   _-- --_     |',
            '  --     --    |',
            ' --   .   --   |',
            ' -_       _-   |',
            '   -_   _-     |',
            '      -        |'])
        self.assertEqual(cliu.importance, 3)


class CLIBaseUrlError(TestCase):

    def test___init__(self):
        from kamaki.cli.errors import CLIBaseUrlError
        for service in ('', 'some service'):
            clibue = CLIBaseUrlError(service=service)
            self.assertEqual('%s' % clibue, 'No URL for %s\n' % service)
            self.assertEqual(clibue.importance, 2)


class CLISyntaxError(TestCase):

    def test___init__(self):
        from kamaki.cli.errors import CLISyntaxError
        clise = CLISyntaxError()
        self.assertEqual('%s' % clise, 'Syntax Error\n')
        self.assertEqual(clise.details, [])
        self.assertEqual(clise.importance, 1)


class CLIInvalidArgument(TestCase):

    def test___init__(self):
        from kamaki.cli.errors import CLIInvalidArgument
        cliia = CLIInvalidArgument()
        self.assertEqual('%s' % cliia, 'Invalid Argument\n')
        self.assertEqual(cliia.details, [])
        self.assertEqual(cliia.importance, 1)


class CLIUnknownCommand(TestCase):

    def test___init__(self):
        from kamaki.cli.errors import CLIUnknownCommand
        cliec = CLIUnknownCommand()
        self.assertEqual('%s' % cliec, 'Unknown Command\n')
        self.assertEqual(cliec.details, [])
        self.assertEqual(cliec.importance, 1)


class CLICmdSpecError(TestCase):

    def test___init__(self):
        from kamaki.cli.errors import CLICmdSpecError
        clicse = CLICmdSpecError()
        self.assertEqual('%s' % clicse, 'Command Specification Error\n')
        self.assertEqual(clicse.details, [])
        self.assertEqual(clicse.importance, 0)


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
    failure_collector += r.errors
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
        if len(failure_collector):
            from sys import exit
            exit(1)


if __name__ == '__main__':
    from sys import argv
    main(argv)
