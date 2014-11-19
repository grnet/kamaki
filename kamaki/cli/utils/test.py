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

from unittest import TestCase
from tempfile import NamedTemporaryFile
from mock import patch, call
from itertools import product
from io import StringIO


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

    @patch('kamaki.cli.utils.dumps', return_value=u'(dumps output)')
    def test_print_json(self, JD):
        from kamaki.cli.utils import print_json, INDENT_TAB
        out = StringIO()
        print_json(u'some data', out)
        JD.assert_called_once_with(u'some data', indent=INDENT_TAB)
        self.assertEqual(out.getvalue(), u'(dumps output)\n')

    def test_print_dict(self):
        from kamaki.cli.utils import print_dict, INDENT_TAB
        out = StringIO()
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
                    print_dict(*args, out=out)
                    exp_calls = u''
                    for i, (k, v) in enumerate(d.items()):
                        if k in exclude:
                            continue
                        str_k = u' ' * indent
                        str_k += u'%s.' % (i + 1) if with_enumeration else u''
                        str_k += u'%s:' % k
                        if isinstance(v, dict):
                            self.assertEqual(
                                PD.mock_calls[pd_calls],
                                call(
                                    v,
                                    exclude,
                                    indent + INDENT_TAB,
                                    recursive_enumeration,
                                    recursive_enumeration,
                                    out))
                            pd_calls += 1
                            exp_calls += str_k + '\n'
                        elif isinstance(v, list) or isinstance(v, tuple):
                            self.assertEqual(
                                PL.mock_calls[pl_calls],
                                call(
                                    v,
                                    exclude,
                                    indent + INDENT_TAB,
                                    recursive_enumeration,
                                    recursive_enumeration,
                                    out))
                            pl_calls += 1
                            exp_calls += str_k + '\n'
                        else:
                            exp_calls += u'%s %s\n' % (str_k, v)
                    self.assertEqual(exp_calls, out.getvalue())
                    out = StringIO()

    def test_print_list(self):
        from kamaki.cli.utils import print_list, INDENT_TAB
        out = StringIO()
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
                    print_list(*args, out=out)
                    exp_calls = ''
                    for i, v in enumerate(l):
                        str_v = u' ' * indent
                        str_v += u'%s.' % (i + 1) if with_enumeration else u''
                        if isinstance(v, dict):
                            if with_enumeration:
                                exp_calls += str_v + '\n'
                            elif i and i < len(l):
                                exp_calls += u'\n'
                            self.assertEqual(
                                PD.mock_calls[pd_calls],
                                call(
                                    v,
                                    exclude,
                                    indent + (
                                        INDENT_TAB if with_enumeration else 0),
                                    recursive_enumeration,
                                    recursive_enumeration,
                                    out))
                            pd_calls += 1
                        elif isinstance(v, list) or isinstance(v, tuple):
                            if with_enumeration:
                                exp_calls += str_v + '\n'
                            elif i and i < len(l):
                                exp_calls += u'\n'
                            self.assertEqual(
                                PL.mock_calls[pl_calls],
                                call(
                                    v,
                                    exclude,
                                    indent + INDENT_TAB,
                                    recursive_enumeration,
                                    recursive_enumeration,
                                    out))
                            pl_calls += 1
                        elif ('%s' % v) in exclude:
                            continue
                        else:
                            exp_calls += u'%s%s\n' % (str_v, v)
                    self.assertEqual(out.getvalue(), exp_calls)
                    out = StringIO()

    @patch('kamaki.cli.utils.print_dict')
    @patch('kamaki.cli.utils.print_list')
    @patch('kamaki.cli.utils.bold', return_value='bold')
    def test_print_items(self, bold, PL, PD):
        from kamaki.cli.utils import print_items, INDENT_TAB
        for args in product(
                (
                    42, None, 'simple outputs',
                    [1, 2, 3], {1: 1, 2: 2}, (3, 4),
                    ({'k': 1, 'id': 2}, [5, 6, 7], (8, 9), '10')),
                (('id', 'name'), ('something', 2), ('lala', )),
                (False, True),
                (False, True)):
            items, title, with_enumeration, with_redundancy = args
            pl_counter, pd_counter = len(PL.mock_calls), len(PD.mock_calls)
            bold_counter, out_counter = len(bold.mock_calls), 0
            out = StringIO()
            print_items(*args, out=out)
            out.seek(0)
            if not (isinstance(items, dict) or isinstance(
                    items, list) or isinstance(items, tuple)):
                if items:
                    self.assertEqual(out.getvalue(), '%s\n' % items)
            else:
                for i, item in enumerate(items):
                    if with_enumeration:
                        exp_str = '%s. ' % (i + 1)
                        self.assertEqual(out.read(len(exp_str)), exp_str)
                    if isinstance(item, dict):
                        title = sorted(set(title).intersection(item))
                        pick = item.get if with_redundancy else item.pop
                        header = ' '.join('%s' % pick(key) for key in title)
                        if header:
                            self.assertEqual(
                                bold.mock_calls[bold_counter], call(header))
                            self.assertEqual(out.read(5), 'bold\n')
                            bold_counter += 1
                        else:
                            out.read(1)
                        self.assertEqual(
                            PD.mock_calls[pd_counter],
                            call(item, indent=INDENT_TAB, out=out))
                        pd_counter += 1
                    elif isinstance(item, list) or isinstance(item, tuple):
                        self.assertEqual(
                            PL.mock_calls[pl_counter],
                            call(item, indent=INDENT_TAB, out=out))
                        pl_counter += 1
                    else:
                        exp_str = u' %s\n' % item
                        self.assertEqual(out.read(len(exp_str)), exp_str)

    def test_format_size(self):
        from kamaki.cli.utils import format_size
        from kamaki.cli import CLIError
        for v in ('wrong', {1: '1', 2: '2'}, ('tuples', 'not OK'), [1, 2]):
            self.assertRaises(CLIError, format_size, v)
        for step, B, K, M, G, T in (
                (1000, 'B', 'KB', 'MB', 'GB', 'TB'),
                (1024, 'B', 'KiB', 'MiB', 'GiB', 'TiB')):
            Ki, Mi, Gi = step, step * step, step * step * step
            for before, after in (
                    (0, '0' + B), (512, '512' + B), (
                        Ki - 1, '%s%s' % (step - 1, B)),
                    (Ki, '1' + K), (42 * Ki, '42' + K), (
                        Mi - 1, '%s.99%s' % (step - 1, K)),
                    (Mi, '1' + M), (42 * Mi, '42' + M), (
                        Ki * Mi - 1, '%s.99%s' % (step - 1, M)),
                    (Gi, '1' + G), (42 * Gi, '42' + G), (
                        Mi * Mi - 1, '%s.99%s' % (step - 1, G)),
                    (Mi * Mi, '1' + T), (42 * Mi * Mi, '42' + T), (
                        Mi * Gi - 1, '%s.99%s' % (step - 1, T)), (
                        42 * Mi * Gi, '%s%s' % (42 * Ki, T))):
                self.assertEqual(format_size(before, step == 1000), after)

    def test_to_bytes(self):
        from kamaki.cli.utils import to_bytes
        for v in ('wrong', 'KABUM', 'kbps', 'kibps'):
            self.assertRaises(ValueError, to_bytes, v, 'B')
            self.assertRaises(ValueError, to_bytes, 42, v)
        for v in ([1, 2, 3], ('kb', 'mb'), {'kb': 1, 'byte': 2}):
            self.assertRaises(TypeError, to_bytes, v, 'B')
            self.assertRaises(AttributeError, to_bytes, 42, v)
        kl, ki = 1000, 1024
        for size, (unit, factor) in product(
                (0, 42, 3.14, 1023, 10000),
                (
                    ('B', 1), ('b', 1),
                    ('KB', kl), ('KiB', ki),
                    ('mb', kl * kl), ('mIb', ki * ki),
                    ('gB', kl * kl * kl), ('GIB', ki * ki * ki),
                    ('TB', kl * kl * kl * kl), ('tiB', ki * ki * ki * ki))):
            self.assertEqual(to_bytes(size, unit), int(size * factor))

    def test_dict2file(self):
        from kamaki.cli.utils import dict2file, INDENT_TAB
        for d, depth in product((
                    {'k': 42},
                    {'k1': 'v1', 'k2': [1, 2, 3], 'k3': {'k': 'v'}},
                    {'k1': {
                        'k1.1': 'v1.1',
                        'k1.2': [1, 2, 3],
                        'k1.3': {'k': 'v'}}}),
                (-42, 0, 42)):
            exp = ''
            exp_d = []
            exp_l = []
            exp, exp_d, exp_l = '', [], []
            with NamedTemporaryFile() as f:
                for k, v in d.items():
                    sfx = '\n'
                    if isinstance(v, dict):
                        exp_d.append(call(v, f, depth + 1))
                    elif isinstance(v, tuple) or isinstance(v, list):
                        exp_l.append(call(v, f, depth + 1))
                    else:
                        sfx = '%s\n' % v
                    exp += '%s%s: %s' % (
                        ' ' * (depth * INDENT_TAB), k, sfx)
                with patch('kamaki.cli.utils.dict2file') as D2F:
                    with patch('kamaki.cli.utils.list2file') as L2F:
                        dict2file(d, f, depth)
                        f.seek(0)
                        self.assertEqual(f.read(), exp)
                        self.assertEqual(L2F.mock_calls, exp_l)
                        self.assertEqual(D2F.mock_calls, exp_d)

    def test_list2file(self):
        from kamaki.cli.utils import list2file, INDENT_TAB
        for l, depth in product(
                (
                    (1, 2, 3),
                    [1, 2, 3],
                    ('v', [1, 2, 3], (1, 2, 3), {'1': 1, 2: '2', 3: 3}),
                    ['v', {'k1': 'v1', 'k2': [1, 2, 3], 'k3': {1: '1'}}]),
                (-42, 0, 42)):
            with NamedTemporaryFile() as f:
                exp, exp_d, exp_l = '', [], []
                for v in l:
                    if isinstance(v, dict):
                        exp_d.append(call(v, f, depth + 1))
                    elif isinstance(v, list) or isinstance(v, tuple):
                        exp_l.append(call(v, f, depth + 1))
                    else:
                        exp += '%s%s\n' % (' ' * INDENT_TAB * depth, v)
                with patch('kamaki.cli.utils.dict2file') as D2F:
                    with patch('kamaki.cli.utils.list2file') as L2F:
                        list2file(l, f, depth)
                        f.seek(0)
                        self.assertEqual(f.read(), exp)
                        self.assertEqual(L2F.mock_calls, exp_l)
                        self.assertEqual(D2F.mock_calls, exp_d)

    def test_split_input(self):
        from kamaki.cli.utils import split_input
        for line, expected in (
                ('set key="v1"', ['set', 'key=v1']),
                ('unparsable', ['unparsable']),
                ('"parsable"', ['parsable']),
                ('"parse" out', ['parse', 'out']),
                ('"one', ['"one']),
                ('two" or" more"', ['two or', 'more"']),
                ('Go "down \'deep " deeper \'bottom \' up" go\' up" !', [
                    'Go', "down 'deep ", 'deeper', 'bottom ',
                    'up go\' up', '!']),
                ('Is "this" a \'parsed\' string?', [
                    'Is', 'this', 'a', 'parsed', 'string?'])):
            self.assertEqual(split_input(line), expected)

    def test_remove_from_items(self):
        from kamaki.cli.utils import remove_from_items
        for v in ('wrong', [1, 2, 3], [{}, 2, {}]):
            self.assertRaises(AssertionError, remove_from_items, v, 'none')
        d = dict(k1=1, k2=dict(k2=2, k3=3), k3=3, k4=4)
        for k in (d.keys() + ['kN']):
            tmp1, tmp2 = dict(d), dict(d)
            remove_from_items([tmp1, ], k)
            tmp1.pop(k, None)
            self.assert_dicts_are_equal(tmp1, tmp2)
        for k in (d.keys() + ['kN']):
            tmp1, tmp2 = dict(d), dict(d)
            remove_from_items([tmp1, tmp2], k)
            self.assert_dicts_are_equal(tmp1, tmp2)

    def test_filter_dicts_by_dict(self):
        from kamaki.cli.utils import filter_dicts_by_dict

        dlist = [
            dict(k1='v1', k2='v2', k3='v3'),
            dict(k1='v1'),
            dict(k2='v2', k3='v3'),
            dict(k1='V1', k3='V3'),
            dict()]
        for l, f, em, cs, exp in (
                (dlist, dlist[2], True, False, dlist[0:1] + dlist[2:3]),
                (dlist, dlist[1], True, False, dlist[0:2] + dlist[3:4]),
                (dlist, dlist[1], True, True, dlist[0:2]),
                (dlist, {'k3': 'v'}, True, False, []),
                (dlist, {'k3': 'v'}, False, False, dlist[0:1] + dlist[2:4]),
                (dlist, {'k3': 'v'}, False, True, dlist[0:1] + dlist[2:3]),
                (dlist, {'k3': 'v'}, True, True, []),
                (dlist, dlist[4], True, False, dlist),
                ):
            self.assertEqual(exp, filter_dicts_by_dict(l, f, em, cs))


if __name__ == '__main__':
    from sys import argv
    from kamaki.cli.test import runTestCase
    runTestCase(UtilsMethods, 'UtilsMethods', argv[1:])
