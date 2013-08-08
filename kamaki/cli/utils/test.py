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
#from tempfile import NamedTemporaryFile
from mock import patch, call
from itertools import product


class UtilsMethods(TestCase):

    def assert_dicts_are_equal(self, d1, d2):
        for k, v in d1.items():
            self.assertTrue(k in d2)
            if isinstance(v, dict):
                self.assert_dicts_are_equal(v, d2[k])
            else:
                self.assertEqual(unicode(v), unicode(d2[k]))

    def test_guess_mime_type(self):
        from kamaki.cli.utils import guess_mime_type
        from mimetypes import guess_type
        for args in product(
                ('file.txt', 'file.png', 'file.zip', 'file.gz', None, 'X'),
                ('a type', None),
                ('an/encoding', None)):
            filename, ctype, cencoding = args
            if filename:
                exp_type, exp_enc = guess_type(filename)
                self.assertEqual(
                    guess_mime_type(*args),
                    (exp_type or ctype, exp_enc or cencoding))
            else:
                self.assertRaises(AssertionError, guess_mime_type, *args)

    @patch('kamaki.cli.utils.dumps', return_value='(dumps output)')
    @patch('kamaki.cli.utils._print')
    def test_print_json(self, PR, JD):
        from kamaki.cli.utils import print_json, INDENT_TAB
        print_json('some data')
        JD.assert_called_once_with('some data', indent=INDENT_TAB)
        PR.assert_called_once_with('(dumps output)')

    @patch('kamaki.cli.utils._print')
    def test_print_dict(self, PR):
        from kamaki.cli.utils import print_dict, INDENT_TAB
        call_counter = 0
        self.assertRaises(AssertionError, print_dict, 'non-dict think')
        self.assertRaises(AssertionError, print_dict, {}, indent=-10)
        for args in product(
                (
                    {'k1': 'v1'},
                    {'k1': 'v1', 'k2': 'v2'},
                    {'k1': 'v1', 'k2': 'v2', 'k3': 'v3'},
                    {'k1': 'v1', 'k2': {'k1': 'v1', 'k2': 'v2'}, 'k3': 'v3'},
                    {
                        'k1': {'k1': 'v1', 'k2': 'v2'},
                        'k2': [1, 2, 3],
                        'k3': 'v3'},
                    {
                        'k1': {'k1': 'v1', 'k2': 'v2'},
                        'k2': 42,
                        'k3': {'k1': 1, 'k2': [1, 2, 3]}},
                    {
                        'k1': {
                            'k1': 'v1',
                            'k2': [1, 2, 3],
                            'k3': {'k1': [(1, 2)]}},
                        'k2': (3, 4, 5),
                        'k3': {'k1': 1, 'k2': [1, 2, 3]}}),
                (tuple(), ('k1', ), ('k1', 'k2')),
                (0, 1, 2, 9), (False, True), (False, True)):
            d, exclude, indent, with_enumeration, recursive_enumeration = args
            with patch('kamaki.cli.utils.print_dict') as PD:
                with patch('kamaki.cli.utils.print_list') as PL:
                    pd_calls, pl_calls = 0, 0
                    print_dict(*args)
                    exp_calls = []
                    for i, (k, v) in enumerate(d.items()):
                        if k in exclude:
                            continue
                        str_k = ' ' * indent
                        str_k += '%s.' % (i + 1) if with_enumeration else ''
                        str_k += '%s:' % k
                        if isinstance(v, dict):
                            self.assertEqual(
                                PD.mock_calls[pd_calls],
                                call(
                                    v,
                                    exclude,
                                    indent + INDENT_TAB,
                                    recursive_enumeration,
                                    recursive_enumeration))
                            pd_calls += 1
                            exp_calls.append(call(str_k))
                        elif isinstance(v, list) or isinstance(v, tuple):
                            self.assertEqual(
                                PL.mock_calls[pl_calls],
                                call(
                                    v,
                                    exclude,
                                    indent + INDENT_TAB,
                                    recursive_enumeration,
                                    recursive_enumeration))
                            pl_calls += 1
                            exp_calls.append(call(str_k))
                        else:
                            exp_calls.append(call('%s %s' % (str_k, v)))
                    real_calls = PR.mock_calls[call_counter:]
                    call_counter = len(PR.mock_calls)
                    self.assertEqual(sorted(real_calls), sorted(exp_calls))

    @patch('kamaki.cli.utils._print')
    def test_print_list(self, PR):
        from kamaki.cli.utils import print_list, INDENT_TAB
        call_counter = 0
        self.assertRaises(AssertionError, print_list, 'non-list non-tuple')
        self.assertRaises(AssertionError, print_list, {}, indent=-10)
        for args in product(
                (
                    ['v1', ],
                    ('v2', 'v3'),
                    [1, '2', 'v3'],
                    ({'k1': 'v1'}, 2, 'v3'),
                    [(1, 2), 'v2', [(3, 4), {'k3': [5, 6], 'k4': 7}]]),
                (tuple(), ('v1', ), ('v1', 1), ('v1', 'k3')),
                (0, 1, 2, 9), (False, True), (False, True)):
            l, exclude, indent, with_enumeration, recursive_enumeration = args
            with patch('kamaki.cli.utils.print_dict') as PD:
                with patch('kamaki.cli.utils.print_list') as PL:
                    pd_calls, pl_calls = 0, 0
                    print_list(*args)
                    exp_calls = []
                    for i, v in enumerate(l):
                        str_v = ' ' * indent
                        str_v += '%s.' % (i + 1) if with_enumeration else ''
                        if isinstance(v, dict):
                            if with_enumeration:
                                exp_calls.append(call(str_v))
                            elif i and i < len(l):
                                exp_calls.append(call())
                            self.assertEqual(
                                PD.mock_calls[pd_calls],
                                call(
                                    v,
                                    exclude,
                                    indent + (
                                        INDENT_TAB if with_enumeration else 0),
                                    recursive_enumeration,
                                    recursive_enumeration))
                            pd_calls += 1
                        elif isinstance(v, list) or isinstance(v, tuple):
                            if with_enumeration:
                                exp_calls.append(call(str_v))
                            elif i and i < len(l):
                                exp_calls.append(call())
                            self.assertEqual(
                                PL.mock_calls[pl_calls],
                                call(
                                    v,
                                    exclude,
                                    indent + INDENT_TAB,
                                    recursive_enumeration,
                                    recursive_enumeration))
                            pl_calls += 1
                        elif ('%s' % v) in exclude:
                            continue
                        else:
                            exp_calls.append(call('%s%s' % (str_v, v)))
                    real_calls = PR.mock_calls[call_counter:]
                    call_counter = len(PR.mock_calls)
                    self.assertEqual(sorted(real_calls), sorted(exp_calls))


if __name__ == '__main__':
    from sys import argv
    from kamaki.cli.test import runTestCase
    runTestCase(UtilsMethods, 'UtilsMethods', argv[1:])
