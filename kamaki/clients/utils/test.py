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

from unittest import TestCase
from tempfile import TemporaryFile
from itertools import product

from kamaki.clients import utils


def _try(assertfoo, foo, *args):
    try:
        return assertfoo(foo(*args))
    except AssertionError:
        argstr = '( '
        for arg in args:
            argstr += '"%s" ' % arg
        argstr += ')'
        print('::: Method %s failed with args %s' % (foo, argstr))
        raise

filter_examples = [
    ('', dict(), dict(), dict()),
    (
        'key',
        dict(key1='v1', key2='v2', v=dict(key='v'), val1='k1', val2='k2'),
        dict(key1='v1', key2='v2'),
        dict(v=dict(key='v'), val1='k1', val2='k2')),
    (
        'val',
        dict(key1='v1', key2='v2', val=dict(key='v'), val1='k1', val2='k2'),
        dict(val1='k1', val2='k2', val=dict(key='v')),
        dict(key1='v1', key2='v2')),
    (
        'kv',
        dict(kvm='in', mkv='out', kv=''),
        dict(kvm='in', kv=''),
        dict(mkv='out'))]


class Utils(TestCase):

    def assert_dicts_are_equal(self, d1, d2):
        for k, v in d1.items():
            self.assertTrue(k in d2)
            if isinstance(v, dict):
                self.assert_dicts_are_equal(v, d2[k])
            else:
                self.assertEqual(unicode(v), unicode(d2[k]))

    def test__matches(self):
        for args in (
                ('example', 'example'), ('example', 'example', True),
                ('example', 'example', False), ('example0', 'example', False),
                ('example', '', False), ('', ''),
                ('', '', True), ('', '', False)):
            _try(self.assertTrue, utils._matches, *args)
        for args in (
                ('', 'example'), ('example', ''),
                ('example', 'example0'), ('example0', 'example'),
                ('example', 'example0', True), ('example', 'example0', False),
                ('example0', 'example'), ('example0', 'example', True)):
            _try(self.assertFalse, utils._matches, *args)

    def test_filter_out(self):
        for key, src, exp_in, exp_out in filter_examples:
            r = utils.filter_out(src, key)
            self.assert_dicts_are_equal(r, exp_out)
            for k in exp_in:
                self.assertFalse(k in r)
            r = utils.filter_out(src, key, True)
            if key in src:
                expected = dict(src)
                expected.pop(key)
                self.assert_dicts_are_equal(r, expected)
            else:
                self.assert_dicts_are_equal(r, src)

    def test_filter_in(self):
        for key, src, exp_in, exp_out in filter_examples:
            r = utils.filter_in(src, key)
            self.assert_dicts_are_equal(r, exp_in)
            for k in exp_out:
                self.assertFalse(k in r)
            r = utils.filter_in(src, key, True)
            if key in src:
                self.assert_dicts_are_equal(r, {key: src[key]})
            else:
                self.assert_dicts_are_equal(r, dict())

    def test_path4url(self):
        utf = u'\u03a6\u03bf\u03cd\u03c4\u03c3\u03bf\u03c2'.encode('utf-8')
        for expected, args in (
                ('', ('')),
                ('/path1/path2', ('path1', 'path2')),
                ('/1/number/0.28', (1, 'number', 0.28)),
                ('/1/n/u/m/b/er/X', ('//1//', '//n//u///m////b/er/', 'X//')),
                ('/p1/%s/p2' % utf.decode('utf-8'), ('p1', utf, 'p2'))):
            self.assertEqual(utils.path4url(*args), expected)

    def test_readall(self):
        tstr = '1234567890'
        with TemporaryFile() as f:
            f.write(tstr)
            f.flush()
            f.seek(0)
            self.assertEqual(utils.readall(f, 5), tstr[:5])
            self.assertEqual(utils.readall(f, 10), tstr[5:])
            self.assertEqual(utils.readall(f, 1), '')
            self.assertRaises(IOError, utils.readall, f, 1, 0)

    def test_escape_ctrl_chars(self):
        gr_synnefo = u'\u03c3\u03cd\u03bd\u03bd\u03b5\u03c6\u03bf'
        gr_kamaki = u'\u03ba\u03b1\u03bc\u03ac\u03ba\u03b9'

        char_pairs = (
            ('\b', '\\x08'), ('\n', '\\n'), ('\a', '\\x07'), ('\f', '\\x0c'),
            ('\t', '\\t'), ('\v', '\\x0b'), ('\r', '\\r'), ('\072', ':'),
            ('\016', '\\x0e'), ('\\', '\\'), ('\\n', '\\n'), ("'", '\''),
            ('"', '"'), (u'\u039f\x89', u'\u039f\\x89'),
        )

        for orig_char, esc_char in char_pairs:
            for word1, word2 in product(
                    ('synnefo', gr_kamaki), ('kamaki', gr_synnefo)):
                orig_str = word1 + orig_char + word2
                esc_str = word1 + esc_char + word2
                self.assertEqual(utils.escape_ctrl_chars(orig_str), esc_str)

if __name__ == '__main__':
    from sys import argv
    from kamaki.clients.test import runTestCase
    runTestCase(Utils, 'clients.utils methods', argv[1:])
