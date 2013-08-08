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
#from mock import patch, call
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

    def test_pretty_keys(self):
        from kamaki.cli.utils import pretty_keys
        for args, exp in (
                (
                    ({'k1': 'v1', 'k1_k2': 'v2'}, ),
                    {'k1': 'v1', 'k1 k2': 'v2'}),
                (
                    ({'k1': 'v1', 'k1_k2': 'v2'}, '1'),
                    {'k': 'v1', 'k _k2': 'v2'}),
                (
                    ({'k1_k2': 'v1', 'k1': {'k2': 'v2', 'k2_k3': 'v3'}}, ),
                    {'k1 k2': 'v1', 'k1': {'k2': 'v2', 'k2_k3': 'v3'}}),
                (
                    (
                        {'k1_k2': 'v1', 'k1': {'k2': 'v2', 'k2_k3': 'v3'}},
                        '_',
                        True),
                    {'k1 k2': 'v1', 'k1': {'k2': 'v2', 'k2 k3': 'v3'}}),
                (
                    (
                        {
                            'k1_k2': {'k_1': 'v_1', 'k_2': {'k_3': 'v_3'}},
                            'k1': {'k2': 'v2', 'k2_k3': 'v3'}},
                        '_',
                        True),
                    {
                        'k1 k2': {'k 1': 'v_1', 'k 2': {'k 3': 'v_3'}},
                        'k1': {'k2': 'v2', 'k2 k3': 'v3'}}),
                (
                    (
                        {
                            'k1_k2': {'k_1': 'v_1', 'k_2': {'k_3': 'v_3'}},
                            'k1': {'k2': 'v2', 'k2_k3': 'v3'}},
                        '1',
                        True),
                    {
                        'k _k2': {'k_': 'v_1', 'k_2': {'k_3': 'v_3'}},
                        'k': {'k2': 'v2', 'k2_k3': 'v3'}})
            ):
            initial = dict(args[0])
            self.assert_dicts_are_equal(pretty_keys(*args), exp)
            self.assert_dicts_are_equal(initial, args[0])


if __name__ == '__main__':
    from sys import argv
    from kamaki.cli.test import runTestCase
    runTestCase(UtilsMethods, 'UtilsMethods', argv[1:])
