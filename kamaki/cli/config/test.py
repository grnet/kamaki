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

from mock import patch, call
from unittest import TestCase
from itertools import product
import os
from tempfile import NamedTemporaryFile
from io import StringIO

from kamaki.cli.config import HEADER
from kamaki.cli import errors


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

    def setUp(self):
        self.f = NamedTemporaryFile()

        from kamaki.cli.config import DEFAULTS

        self.DEFAULTS = dict()
        for k, v in DEFAULTS.items():
            self.DEFAULTS[k] = dict(v) if isinstance(v, dict) else v

        self.config_file_content = [
            HEADER,
            '[global]\n',
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

    def tearDown(self):
        try:
            self.f.close()
        except Exception:
            pass
        finally:
            from kamaki.cli.config import DEFAULTS
            keys = DEFAULTS.keys()
            for k in keys:
                DEFAULTS.pop(k)
            for k, v in self.DEFAULTS.items():
                DEFAULTS[k] = v

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
                    'kamaki.cli.config.Config.cloud_name',
                    return_value=_2value_gen.next()) as cloud_name:
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

                self.assertEqual(cloud_name.mock_calls, gen_call)

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

    def test_cloud_name(self):
        from kamaki.cli.config import (
            Config, CLOUD_PREFIX, InvalidCloudNameError)
        cn = Config.cloud_name
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
            f.seek(0)
            _cnf = Config(path=f.name)
            self.assertEqual(
                sorted(['global.%s' % sample]), sorted(_cnf.rescue_old_file()))
        del _cnf

        content2, sample = list(content0), 'http://www.example2.org'
        content2.insert(2, 'url = %s\n' % sample)
        err = StringIO()

        with make_file(content2) as f:
            _cnf = Config(path=f.name)
            self.assertRaises(
                errors.CLISyntaxError, _cnf.rescue_old_file, err=err)
        del _cnf

        content3 = list(content0)
        content3.insert(
            2, 'url = http://example1.com\nurl = http://example2.com\n')

        with make_file(content3) as f:
            _cnf = Config(path=f.name)
            self.assertRaises(
                errors.CLISyntaxError, _cnf.rescue_old_file, err=err)
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
                self.assertEqual(0.12, _cnf.guess_version())
                exp = 'All heuristics failed, cannot decide\n'
                logf.file.seek(- len(exp), 2)
                self.assertEqual(exp, logf.read())

        content0 = list(self.config_file_content)

        with make_file(content0) as f:
            with make_log_file() as logf:
                _cnf = Config(path=f.name)
                self.assertEqual(0.10, _cnf.guess_version())

        for term in ('url', 'token'):
            content1 = list(content0)
            content1.insert(2, '%s = some_value' % term)

            with make_file(content1) as f:
                with make_log_file() as logf:
                    _cnf = Config(path=f.name)
                    self.assertEqual(0.8, _cnf.guess_version())
                    exp = 'config file has an old global section\n'
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

    def test__load_defaults(self):
        from kamaki.cli.config import Config, DEFAULTS
        _cnf = Config(path=self.f.name)

        with patch('kamaki.cli.config.Config.set') as c_set:
            _cnf._load_defaults()
            for i, (section, options) in enumerate(DEFAULTS.items()):
                for j, (option, val) in enumerate(options.items()):
                    self.assertEqual(
                        c_set.mock_calls[(i + 1) * j],
                        call(section, option, val))

    def test__get_dict(self):
        from kamaki.cli.config import Config, CLOUD_PREFIX, DEFAULTS

        def make_file(lines):
            f = NamedTemporaryFile()
            f.writelines(lines)
            f.flush()
            return f

        with make_file([]) as f:
            _cnf = Config(path=f.name)
            for term in ('global', CLOUD_PREFIX):
                self.assertEqual(DEFAULTS[term], _cnf._get_dict(term))
            for term in ('nosection', ''):
                self.assertEqual({}, _cnf._get_dict(term))

        with make_file(self.config_file_content) as f:
            _cnf = Config(path=f.name)
            for term in ('global', CLOUD_PREFIX):
                self.assertNotEqual(DEFAULTS[term], _cnf._get_dict(term))

    def test_reload(self):
        from kamaki.cli.config import Config
        _cnf = Config(path=self.f.name)

        with patch('kamaki.cli.config.Config.__init__') as i:
            _cnf.reload()
            i.assert_called_once_with(self.f.name)

    @patch('kamaki.cli.config.Config.get_cloud', return_value='get cloud')
    def test_get(self, get_cloud):
        from kamaki.cli.config import Config
        _cnf = Config(path=self.f.name)
        self.assertEqual('pithos', _cnf.get('global', 'file_cli'))
        self.assertEqual(get_cloud.mock_calls, [])
        for opt, sec in (('cloud', 'non-existing'), ('non-opt', 'exists')):
            self.assertEqual(None, _cnf.get(opt, sec))
            self.assertEqual(get_cloud.mock_calls, [])
        self.assertEqual('get cloud', _cnf.get('cloud.demo', 'url'))
        self.assertEqual(get_cloud.mock_calls[-1], call('demo', 'url'))

    def test_set(self):
        from kamaki.cli.config import Config, CLOUD_PREFIX
        _cnf = Config(path=self.f.name)

        with patch(
                'kamaki.cli.config.Config.cloud_name',
                return_value='cn') as cloud_name:
            with patch(
                    'kamaki.cli.config.Config.set_cloud',
                    return_value='sc') as set_cloud:
                self.assertEqual(
                    'sc', _cnf.set('%s.sec' % CLOUD_PREFIX, 'opt', 'val'))
                self.assertEqual(
                    cloud_name.mock_calls[-1],
                    call('%s "sec"' % CLOUD_PREFIX))
                self.assertEqual(
                    set_cloud.mock_calls[-1], call('cn', 'opt', 'val'))

                self.assertTrue(len(_cnf.items('global')) > 0)
                self.assertEqual(None, _cnf.set('global', 'opt', 'val'))
                self.assertTrue(('opt', 'val') in _cnf.items('global'))

                self.assertTrue(len(_cnf.items('new')) == 0)
                self.assertEqual(None, _cnf.set('new', 'opt', 'val'))
                self.assertTrue(('opt', 'val') in _cnf.items('new'))

    def test_remove_option(self):
        from kamaki.cli.config import Config
        _cnf = Config(path=self.f.name)

        self.assertEqual(len(_cnf.items('no-section')), 0)
        _cnf.remove_option('no-section', 'opt', False)
        self.assertEqual(len(_cnf.items('no-section')), 0)
        _cnf.remove_option('no-section', 'opt', True)
        self.assertEqual(len(_cnf.items('no-section')), 0)

        opt_num = len(_cnf.items('global'))
        self.assertTrue(opt_num > 0)
        _cnf.remove_option('global', 'file_cli', False)
        self.assertEqual(len(_cnf.items('global')), opt_num)
        _cnf.remove_option('global', 'file_cli', True)
        self.assertEqual(len(_cnf.items('global')), opt_num - 1)

        _cnf.set('global', 'server_cli', 'alt-server')
        self.assertTrue(('server_cli', 'alt-server') in _cnf.items('global'))
        self.assertFalse(('server_cli', 'cyclades') in _cnf.items('global'))
        _cnf.remove_option('global', 'server_cli', False)
        self.assertFalse(('server_cli', 'alt-server') in _cnf.items('global'))
        self.assertTrue(('server_cli', 'cyclades') in _cnf.items('global'))
        _cnf.remove_option('global', 'server_cli', True)
        self.assertFalse(('server_cli', 'alt-server') in _cnf.items('global'))
        self.assertFalse(('server_cli', 'cyclades') in _cnf.items('global'))

    def test_remove_from_cloud(self):
        from kamaki.cli.config import Config, CLOUD_PREFIX
        _cnf = Config(path=self.f.name)

        d = dict(k1='v1', k2='v2')
        with patch('kamaki.cli.config.Config.get', return_value=d) as get:
            _cnf.remove_from_cloud('cld', 'k1')
            self.assertEqual(d, dict(k2='v2'))
            self.assertRaises(KeyError, _cnf.remove_from_cloud, 'cld', 'opt')
            self.assertEqual(get.mock_calls, 2 * [call(CLOUD_PREFIX, 'cld')])

    @patch(
        'kamaki.cli.config.Config._get_dict',
        return_value={'k1': 'v1', 'k2': 'v2'})
    def test_keys(self, _get_dict):
        from kamaki.cli.config import Config
        _cnf = Config(path=self.f.name)

        self.assertEqual(
            sorted(['k1', 'k2']), sorted(_cnf.keys('opt', 'boolean')))
        _get_dict.assert_called_once_with('opt', 'boolean')

    @patch(
        'kamaki.cli.config.Config._get_dict',
        return_value={'k1': 'v1', 'k2': 'v2'})
    def test_items(self, _get_dict):
        from kamaki.cli.config import Config
        _cnf = Config(path=self.f.name)

        self.assertEqual(
            sorted([('k1', 'v1'), ('k2', 'v2')]),
            sorted(_cnf.items('opt', 'boolean')))
        _get_dict.assert_called_once_with('opt', 'boolean')

    def test_override(self):
        from kamaki.cli.config import Config
        _cnf = Config(path=self.f.name)

        _cnf.override('sec', 'opt', 'val')
        self.assertEqual(_cnf._overrides['sec']['opt'], 'val')

    def test_safe_to_print(self):
        itemsd = {
            'global': {
                'opt1': 'v1',
                'opt2': 2,
                'opt3': u'\u03c4\u03b9\u03bc\u03ae',
                'opt4': 'un\b\bdeleted'
            }, 'cloud': {
                'cld1': {'url': 'url1', 'token': 'token1'},
                'cld2': {'url': u'\u03bf\u03c5\u03b1\u03c1\u03ad\u03bb'}
            }
        }

        from kamaki.cli.config import Config
        _cnf = Config(path=self.f.name)
        bu_func = Config.items
        try:
            Config.items = (
                lambda cls, opt, include_defaults: itemsd[opt].items())
            saved = _cnf.safe_to_print().split('\n')
            glb, cld = saved[:5], saved[6:]
            self.assertEqual(u'[global]', glb[0])
            self.assertTrue(u'opt1 = v1' in glb)
            self.assertTrue(u'opt2 = 2' in glb)
            self.assertTrue(u'opt3 = \u03c4\u03b9\u03bc\u03ae' in glb)
            self.assertTrue(u'opt4 = un\\x08\\x08deleted' in glb)

            self.assertTrue('[cloud "cld1"]' in cld)
            cld1_i = cld.index('[cloud "cld1"]')
            cld1 = cld[cld1_i: cld1_i + 3]
            self.assertTrue('url = url1' in cld1)
            self.assertTrue('token = token1' in cld1)

            self.assertTrue('[cloud "cld2"]' in cld)
            cld2_i = cld.index('[cloud "cld2"]')
            self.assertEqual(
                u'url = \u03bf\u03c5\u03b1\u03c1\u03ad\u03bb', cld[cld2_i + 1])
        finally:
            Config.items = bu_func

    @patch('kamaki.cli.config.Config.safe_to_print', return_value='rv')
    def test_write(self, stp):
        from kamaki.cli.config import Config
        _cnf = Config(path=self.f.name)
        exp = '%s%s' % (HEADER, 'rv')
        _cnf.write()
        self.f.seek(0)
        self.assertEqual(self.f.read(), exp)
        stp.assert_called_once_with()
        del _cnf


if __name__ == '__main__':
    from sys import argv
    from kamaki.cli.test import runTestCase
    runTestCase(Config, 'Config', argv[1:])
