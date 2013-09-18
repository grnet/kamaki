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
from tempfile import NamedTemporaryFile
from io import StringIO


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

    config_file_content = [
        '#kamaki config file version 0.9\n',
        '[global]\n',
        'max_threads = 5\n',
        'default_cloud = ~mycloud\n',
        'file_cli = pithos\n',
        'history_file = /home/user/.kamaki.history\n',
        'colors = off\n',
        'config_cli = config\n',
        'history_cli = history\n',
        'log_token = off\n',
        'server_cli = cyclades\n',
        'user_cli = astakos\n',
        'log_data = off\n',
        'flavor_cli = cyclades\n',
        'image_cli = image\n',
        'log_file = /home/user/.kamaki.log\n',
        'network_cli = cyclades\n',
        'log_pid = off\n',
        '\n',
        '[cloud "demo"]\n',
        'url = https://demo.example.com\n',
        'token = t0k3n-0f-d3m0-3x4mp13\n',
        '\n',
        '[cloud "~mycloud"]\n',
        'url = https://example.com\n',
        'pithos_container = images\n']

    def setUp(self):
        self.f = NamedTemporaryFile()

    def readDown(self):
        try:
            self.f.close()
        except Exception:
            pass

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
                        call(r, 'k1', 'v1'), call(r, 'k2', 'v2')] * 2)
                    c_remove_section_num += 2
                    self.assertEqual(
                        c_remove_section.mock_calls[-2:], gen_call)
                self.assertEqual(len(c_items.mock_calls), c_items_num)
                self.assertEqual(len(c_set_cloud.mock_calls), c_set_cloud_num)
                self.assertEqual(
                    len(c_remove_section.mock_calls), c_remove_section_num)

    def test__cloud_name(self):
        from kamaki.cli.config import (
            Config, CLOUD_PREFIX, InvalidCloudNameError)
        cn = Config._cloud_name
        self.assertEqual(cn('non%s name' % CLOUD_PREFIX), None)
        for invalid in ('"!@#$%^&())_"', '"a b c"', u'"\xce\xcd"', 'naked'):
            self.assertRaises(
                InvalidCloudNameError, cn, '%s %s' % (CLOUD_PREFIX, invalid))
        for valid in ('word', '~okeanos', 'd0t.ted', 'ha$h#ed'):
            self.assertEqual(cn('%s "%s"' % (CLOUD_PREFIX, valid)), valid)

    def test_rescue_old_file(self):
        from kamaki.cli.config import Config

        content0 = list(self.config_file_content)

        def make_file(lines):
            f = NamedTemporaryFile()
            f.writelines(lines)
            f.flush()
            return f

        with make_file(content0) as f:
            _cnf = Config(path=f.name)
            self.assertEqual([], _cnf.rescue_old_file())
        del _cnf

        content1, sample = list(content0), 'xyz_cli = XYZ_specs'
        content1.insert(2, '%s\n' % sample)

        with make_file(content1) as f:
            _cnf = Config(path=f.name)
            self.assertEqual(['global.%s' % sample], _cnf.rescue_old_file())
        del _cnf

        content2, sample = list(content0), 'http://www.example2.org'
        content2.insert(2, 'url = %s\n' % sample)
        err = StringIO()

        with make_file(content2) as f:
            _cnf = Config(path=f.name)
            self.assertEqual([], _cnf.rescue_old_file(err=err))
            self.assertEqual(
                '... rescue global.url => cloud.default.url\n', err.getvalue())
            self.assertEqual(sample, _cnf.get_cloud('default', 'url'))
        del _cnf

        content3 = list(content0)
        content3.insert(
            2, 'url = http://example1.com\nurl = http://example2.com\n')

        with make_file(content3) as f:
            _cnf = Config(path=f.name)
            self.assertEqual([], _cnf.rescue_old_file(err=err))
            self.assertEqual(
                2 * '... rescue global.url => cloud.default.url\n',
                err.getvalue())
            self.assertEqual(
                'http://example2.com', _cnf.get_cloud('default', 'url'))
        del _cnf

        content4 = list(content0)
        content4.insert(2, 'url = http://example1.com\n')
        content4.append('\n[cloud "default"]\nurl=http://example2.com\n')

        with make_file(content4) as f:
            _cnf = Config(path=f.name)
            from kamaki.cli.errors import CLISyntaxError
            self.assertRaises(CLISyntaxError, _cnf.rescue_old_file)
        del _cnf

        content5 = list(content0)
        extras = [
            ('pithos_cli', 'pithos'), ('store_cli', 'pithos'),
            ('storage_cli', 'pithos'), ('compute_cli', 'cyclades'),
            ('cyclades_cli', 'cyclades')]
        for sample in extras:
            content5.insert(2, '%s = %s\n' % sample)

        with make_file(content5) as f:
            _cnf = Config(path=f.name)
            self.assertEqual(
                sorted(['global.%s = %s' % sample for sample in extras]),
                 sorted(_cnf.rescue_old_file()))

    def test_guess_version(self):
        from kamaki.cli.config import Config
        from kamaki.cli.logger import add_file_logger

        def make_log_file():
            f = NamedTemporaryFile()
            add_file_logger('kamaki.cli.config', filename=f.name)
            return f

        def make_file(lines):
            f = NamedTemporaryFile()
            f.writelines(lines)
            f.flush()
            return f

        with make_file([]) as f:
            with make_log_file() as logf:
                _cnf = Config(path=f.name)
                self.assertEqual(0.9, _cnf.guess_version())
                exp = 'All heuristics failed, cannot decide\n'
                logf.file.seek(- len(exp), 2)
                self.assertEqual(exp, logf.read())

        content0 = list(self.config_file_content)

        with make_file(content0) as f:
            with make_log_file() as logf:
                _cnf = Config(path=f.name)
                self.assertEqual(0.9, _cnf.guess_version())
                exp = '... found cloud "demo"\n'
                logf.seek(- len(exp), 2)
                self.assertEqual(exp, logf.read())

        for term in ('url', 'token'):
            content1 = list(content0)
            content1.insert(2, '%s = some_value' % term)

            with make_file(content1) as f:
                with make_log_file() as logf:
                    _cnf = Config(path=f.name)
                    self.assertEqual(0.8, _cnf.guess_version())
                    exp = '..... config file has an old global section\n'
                    logf.seek(- len(exp), 2)
                    self.assertEqual(exp, logf.read())

    def test_get_cloud(self):
        from kamaki.cli.config import Config, CLOUD_PREFIX

        _cnf = Config(path=self.f.name)
        d = dict(opt1='v1', opt2='v2')
        with patch('kamaki.cli.config.Config.get', return_value=d) as get:
            self.assertEqual('v1', _cnf.get_cloud('mycloud', 'opt1'))
            self.assertEqual(
                get.mock_calls[-1], call(CLOUD_PREFIX, 'mycloud'))
            self.assertRaises(KeyError, _cnf.get_cloud, 'mycloud', 'opt3')
        with patch('kamaki.cli.config.Config.get', return_value=0) as get:
            self.assertRaises(KeyError, _cnf.get_cloud, 'mycloud', 'opt1')

    def test_get_global(self):
        from kamaki.cli.config import Config

        _cnf = Config(path=self.f.name)
        with patch('kamaki.cli.config.Config.get', return_value='val') as get:
            self.assertEqual('val', _cnf.get_global('opt'))
            get.assert_called_once_with('global', 'opt')

    @patch('kamaki.cli.config.Config.set')
    def test_set_cloud(self, c_set):
        from kamaki.cli.config import Config, CLOUD_PREFIX
        _cnf = Config(path=self.f.name)

        d = dict(k='v')
        with patch('kamaki.cli.config.Config.get', return_value=d) as get:
            _cnf.set_cloud('mycloud', 'opt', 'val')
            get.assert_called_once_with(CLOUD_PREFIX, 'mycloud')
            d['opt'] = 'val'
            self.assertEqual(
                c_set.mock_calls[-1], call(CLOUD_PREFIX, 'mycloud', d))

        with patch('kamaki.cli.config.Config.get', return_value=None) as get:
            _cnf.set_cloud('mycloud', 'opt', 'val')
            get.assert_called_once_with(CLOUD_PREFIX, 'mycloud')
            d = dict(opt='val')
            self.assertEqual(
                c_set.mock_calls[-1], call(CLOUD_PREFIX, 'mycloud', d))

        with patch(
                'kamaki.cli.config.Config.get', side_effect=KeyError()) as get:
            _cnf.set_cloud('mycloud', 'opt', 'val')
            get.assert_called_once_with(CLOUD_PREFIX, 'mycloud')
            d = dict(opt='val')
            self.assertEqual(
                c_set.mock_calls[-1], call(CLOUD_PREFIX, 'mycloud', d))

    def test_set_global(self):
        from kamaki.cli.config import Config
        _cnf = Config(path=self.f.name)

        with patch('kamaki.cli.config.Config.set') as c_set:
            _cnf.set_global('opt', 'val')
            c_set.assert_called_once_with('global', 'opt', 'val')


if __name__ == '__main__':
    from sys import argv
    from kamaki.cli.test import runTestCase
    runTestCase(Config, 'Config', argv[1:])
