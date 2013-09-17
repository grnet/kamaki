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

from mock import patch, call
from unittest import TestCase
from itertools import product
import os


def _2steps_gen(limit=2):
    counter, ret = 0, None
    while True:
        if counter >= limit:
            ret = None if ret else 'something'
            counter = 0
        counter += 1
        yield ret

_2value_gen = _2steps_gen()


class Config(TestCase):
    """Test Config methods"""

    @patch('kamaki.cli.config.Config.remove_section')
    @patch('kamaki.cli.config.Config.items', return_value=(
        ('k1', 'v1'), ('k2', 'v2')))
    @patch('kamaki.cli.config.Config.sections', return_value=('a', 'b'))
    @patch('kamaki.cli.config.Config.set_cloud')
    @patch('kamaki.cli.config.Config.read')
    @patch('kamaki.cli.config.Config._load_defaults')
    def test___init__(
            self, _ld, c_read, c_set_cloud, c_sections, c_items,
            c_remove_section):
        from kamaki.cli.config import (
            Config, RawConfigParser, CONFIG_ENV, CONFIG_PATH)
        _ld_num, c_sections_num, c_items_num, c_set_cloud_num = 0, 0, 0, 0
        c_remove_section_num, gen_call = 0, [call('a'), call('b')]
        for path, with_defaults in product((None, '/a/path'), (True, False)):
            with patch(
                    'kamaki.cli.config.Config._cloud_name',
                    return_value=_2value_gen.next()) as _cloud_name:
                cnf = Config(path=path, with_defaults=with_defaults)
                self.assertTrue(isinstance(cnf, RawConfigParser))
                cpath = path or os.environ.get(CONFIG_ENV, CONFIG_PATH)
                self.assertEqual(cnf.path, cpath)
                if with_defaults:
                    _ld_num += 1
                    self.assertEqual(_ld.mock_calls[-1], call())
                self.assertEqual(len(_ld.mock_calls), _ld_num)
                self.assertEqual(c_read.mock_calls[-1], call(cpath))

                c_sections_num += 1
                self.assertEqual(len(c_sections.mock_calls), c_sections_num)
                self.assertEqual(c_sections.mock_calls[-1], call())

                self.assertEqual(_cloud_name.mock_calls, gen_call)

                r = _2value_gen.next()
                if r:
                    c_items_num += 2
                    self.assertEqual(c_items.mock_calls[-2:], gen_call)
                    c_set_cloud_num += 4
                    self.assertEqual(c_set_cloud.mock_calls[-4:], [
                        call(r, 'k1', 'v1'), call(r, 'k2', 'v2'),
                        call(r, 'k1', 'v1'), call(r, 'k2', 'v2')])
                    c_remove_section_num += 2
                    self.assertEqual(
                        c_remove_section.mock_calls[-2:], gen_call)
                self.assertEqual(len(c_items.mock_calls), c_items_num)
                self.assertEqual(len(c_set_cloud.mock_calls), c_set_cloud_num)
                self.assertEqual(
                    len(c_remove_section.mock_calls), c_remove_section_num)


if __name__ == '__main__':
    from sys import argv
    from kamaki.cli.test import runTestCase
    runTestCase(Config, 'Config', argv[1:])
