# Copyright 2012-2013 GRNET S.A. All rights reserved.
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
from argparse import ArgumentParser
from sys import stdout
from progress.bar import ShadyBar

from kamaki.cli.config import Config
from kamaki.cli.utils import spiner


def _add_value(foo, value):
    def wrap(self):
        return foo(self, value)
    return wrap


class Generic(TestCase):

    _waits = []
    _cnf = None
    _grp = None
    _fetched = {}

    def __init__(self, specific=None, config_file=None, group=None):
        super(Generic, self).__init__(specific)
        self._cnf = Config(config_file)
        self._grp = group
        self._waits.append(0.71828)
        for i in range(10):
            self._waits.append(self._waits[-1] * 2.71828)

    def __getitem__(self, key):
        key = self._key(key)
        try:
            return self._fetched[key]
        except KeyError:
            return self._get_from_cnf(key)

    def _key(self, key):
        return ('', key) if isinstance(key, str)\
            else ('', key[0]) if len(key) == 1\
            else key

    def _get_from_cnf(self, key):
        val = 0
        if key[0]:
            val = self._cnf.get('test', '%s_%s' % key)\
                or self._cnf.get(*key)
        if not val:
            val = self._cnf.get('test', key[1])\
                or self._cnf.get('global', key[1])
        self._fetched[key] = val
        return val

    def _safe_progress_bar(self, msg):
        """Try to get a progress bar, but do not raise errors"""
        try:
            wait_bar = ShadyBar(msg)

            def wait_gen(n):
                for i in wait_bar.iter(range(int(n))):
                    yield
                yield
            wait_cb = wait_gen
        except Exception:
            stdout.write('%s:' % msg)
            (wait_bar, wait_cb) = (None, spiner)
        return (wait_bar, wait_cb)

    def _safe_progress_bar_finish(self, progress_bar):
        try:
            progress_bar.finish()
        except Exception:
            print(' DONE')

    def do_with_progress_bar(self, action, msg, items):
        if not items:
            print('%s: DONE' % msg)
            return
        (action_bar, action_cb) = self._safe_progress_bar(msg)
        action_gen = action_cb(len(items))
        for item in items:
            action(item)
            action_gen.next()
        self._safe_progress_bar_finish(action_bar)

    def assert_dicts_are_deeply_equal(self, d1, d2):
        for k, v in d1.items():
            self.assertTrue(k in d2)
            if isinstance(v, dict):
                self.assert_dicts_are_deeply_equal(v, d2[k])
            else:
                self.assertEqual(unicode(v), unicode(d2[k]))

    def test_000(self):
        import inspect
        methods = [method for method in inspect.getmembers(
            self,
            predicate=inspect.ismethod)\
            if method[0].startswith('_test_')]
        failures = 0
        for method in methods:
            stdout.write('Test %s' % method[0][6:])
            try:
                method[1]()
                print(' ...ok')
            except AssertionError:
                print('  FAIL: %s (%s)' % (method[0], method[1]))
                failures += 1
        if failures:
            raise AssertionError('%s failures' % failures)


def init_parser():
    parser = ArgumentParser(add_help=False)
    parser.add_argument('-h', '--help',
        dest='help',
        action='store_true',
        default=False,
        help="Show this help message and exit")
    return parser


def main(argv):

    suiteFew = TestSuite()
    """
    if len(argv) == 0 or argv[0] == 'pithos':
        if len(argv) == 1:
            suiteFew.addTest(unittest.makeSuite(testPithos))
        else:
            suiteFew.addTest(testPithos('test_' + argv[1]))
    """
    if len(argv) == 0 or argv[0] == 'cyclades':
        from kamaki.clients.tests.cyclades import Cyclades
        test_method = 'test_%s' % (argv[1] if len(argv) > 1 else '000')
        suiteFew.addTest(Cyclades(test_method))
    if len(argv) == 0 or argv[0] == 'image':
        from kamaki.clients.tests.image import Image
        test_method = 'test_%s' % (argv[1] if len(argv) > 1 else '000')
        suiteFew.addTest(Image(test_method))
    if len(argv) == 0 or argv[0] == 'astakos':
        from kamaki.clients.tests.astakos import Astakos
        if len(argv) == 1:
            suiteFew.addTest(makeSuite(Astakos))
        else:
            suiteFew.addTest(Astakos('test_' + argv[1]))

    TextTestRunner(verbosity=2).run(suiteFew)

if __name__ == '__main__':
    parser = init_parser()
    args, argv = parser.parse_known_args()
    if len(argv) > 2 or getattr(args, 'help') or len(argv) < 1:
        raise Exception('\tusage: tests.py <group> [command]')
    main(argv)
