# Copyright 2014 GRNET S.A. All rights reserved.
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

from kamaki.clients import blockstorage

clients_pkg = 'kamaki.clients.Client'
utils_pkg = 'kamaki.clients.utils'


class BlockStorageRestClient(TestCase):
    """Block Storage (cinder) REST API unit tests"""

    def setUp(self):
        self.url = 'http://volumes.example.com'
        self.token = 'v01um3s70k3n'
        self.client = blockstorage.BlockStorageRestClient(self.url, self.token)

    @patch('%s.get' % clients_pkg)
    @patch('%s.path4url' % utils_pkg, return_value='path_str')
    def test_volumes_get(self, path4url, get):
        for detail, volume_id, kwargs in product(
                (True, None),
                ('v0lum3-1d', None),
                ({'k': 'v'}, {'success': 1000}, {})):
            self.client.volumes_get(detail, volume_id, **kwargs)
            self.assertEqual(
                path4url.mock_calls[-1],
                call('volumes', 'detail' if detail else volume_id or ''))
            success = kwargs.pop('success', 200)
            self.assertEqual(
                get.mock_calls[-1],
                call('path_str', success=success, **kwargs))

    @patch('%s.post' % clients_pkg)
    @patch('%s.path4url' % utils_pkg, return_value='path_str')
    def test_volumes_post(self, path4url, post):
        keys = (
            'availability_zone', 'source_volid', 'display_description',
            'snapshot_id', 'display_name', 'imageRef', 'volume_type',
            'bootable', 'metadata')
        for args in product(
                ('az', None), ('volId', None), ('dd', None),
                ('sn', None), ('dn', None), ('ir', None), ('vt', None),
                (True, False, None), ({'mk': 'mv'}, None),
                ({'k1': 'v1', 'k2': 'v2'}, {'success': 1000}, {})):
            kwargs = args[-1]
            args = args[:-1]
            for err, size in ((TypeError, None), (ValueError, 'size')):
                self.assertRaises(
                    err, self.client.volumes_post, size, *args, **kwargs)
            size = 42
            self.client.volumes_post(size, *args, **kwargs)
            self.assertEqual(path4url.mock_calls[-1], call('volumes'))
            volume = dict(size=int(size))
            for k, v in zip(keys, args):
                if v is not None:
                    volume[k] = v
            success, jsondata = kwargs.pop('success', 202), dict(volume=volume)
            self.assertEqual(
                post.mock_calls[-1],
                call('path_str', json=jsondata, success=success, **kwargs))

    @patch('%s.put' % clients_pkg)
    @patch('%s.path4url' % utils_pkg, return_value='path_str')
    def test_volumes_put(self, path4url, put):
        keys = (
            'display_description', 'display_name', 'delete_on_termination',
            'metadata')
        for args in product(
                ('dd', None), ('dn', None), (True, False, None),
                ({'mk': 'mv'}, None),
                ({'k1': 'v1', 'k2': 'v2'}, {'success': 1000}, {})):
            kwargs, volid = args[-1], 'v0lum3-1d'
            args = args[:-1]
            self.client.volumes_put(volid, *args, **kwargs)
            self.assertEqual(path4url.mock_calls[-1], call('volumes', volid))
            volume = dict()
            for k, v in zip(keys, args):
                if v is not None:
                    volume[k] = v
            success, jsondata = kwargs.pop('success', 200), dict(volume=volume)
            self.assertEqual(put.mock_calls[-1], call(
                'path_str', json=jsondata, success=success, **kwargs))

    @patch('%s.delete' % clients_pkg)
    @patch('%s.path4url' % utils_pkg, return_value='path_str')
    def test_volumes_delete(self, path4url, delete):
        volid = 'v0lum3-1d'
        for kwargs in (dict(k1='v1', k2='v2'), dict(success=1000), dict()):
            self.client.volumes_delete(volid, **kwargs)
            self.assertEqual(path4url.mock_calls[-1], call('volumes', volid))
            success = kwargs.pop('success', 202)
            self.assertEqual(delete.mock_calls[-1], call(
                'path_str', success=success, **kwargs))

    @patch('%s.get' % clients_pkg)
    @patch('%s.path4url' % utils_pkg, return_value='path_str')
    def test_snapshots_get(self, path4url, get):
        for detail, snapshot_id, kwargs in product(
                (True, None),
                ('v0lum3-1d', None),
                ({'k': 'v'}, {'success': 1000}, {})):
            self.client.snapshots_get(detail, snapshot_id, **kwargs)
            self.assertEqual(
                path4url.mock_calls[-1],
                call('snapshots', 'detail' if detail else snapshot_id or ''))
            success = kwargs.pop('success', 200)
            self.assertEqual(
                get.mock_calls[-1],
                call('path_str', success=success, **kwargs))

    @patch('%s.post' % clients_pkg)
    @patch('%s.path4url' % utils_pkg, return_value='path_str')
    def test_snapshots_post(self, path4url, post):
        keys = ('force', 'display_name', 'display_description')
        for args in product(
                (True, False, None), ('dn', None), ('dd', None),
                ({'k1': 'v1', 'k2': 'v2'}, {'success': 1000}, {})):
            kwargs, volume_id = args[-1], 'v0lum3-1d'
            args = args[:-1]
            self.client.snapshots_post(volume_id, *args, **kwargs)
            self.assertEqual(path4url.mock_calls[-1], call('snapshots'))
            sn = dict(volume_id=volume_id)
            for k, v in zip(keys, args):
                if v is not None:
                    sn[k] = v
            success, json_data = kwargs.pop('success', 202), dict(snapshot=sn)
            self.assertEqual(
                post.mock_calls[-1],
                call('path_str', json=json_data, success=success, **kwargs))

    @patch('%s.put' % clients_pkg)
    @patch('%s.path4url' % utils_pkg, return_value='path_str')
    def test_snapshots_put(self, path4url, put):
        keys = ('display_description', 'display_name')
        for args in product(
                ('dd', None), ('dn', None),
                ({'k1': 'v1', 'k2': 'v2'}, {'success': 1000}, {})):
            kwargs, volid = args[-1], 'v0lum3-1d'
            args = args[:-1]
            self.client.snapshots_put(volid, *args, **kwargs)
            self.assertEqual(path4url.mock_calls[-1], call('snapshots', volid))
            sn = dict()
            for k, v in zip(keys, args):
                if v is not None:
                    sn[k] = v
            success, json_data = kwargs.pop('success', 200), dict(snapshot=sn)
            self.assertEqual(put.mock_calls[-1], call(
                'path_str', json=json_data, success=success, **kwargs))

    @patch('%s.delete' % clients_pkg)
    @patch('%s.path4url' % utils_pkg, return_value='path_str')
    def test_snapshots_delete(self, path4url, delete):
        snid = 'sn4p5h0t-1d'
        for kwargs in (dict(k1='v1', k2='v2'), dict(success=1000), dict()):
            self.client.snapshots_delete(snid, **kwargs)
            self.assertEqual(path4url.mock_calls[-1], call('snapshots', snid))
            success = kwargs.pop('success', 202)
            self.assertEqual(delete.mock_calls[-1], call(
                'path_str', success=success, **kwargs))

    @patch('%s.get' % clients_pkg)
    @patch('%s.path4url' % utils_pkg, return_value='path_str')
    def test_types_set(self, path4url, get):
        for type_id, kwargs in product(
                ('tid', None),
                ({'k1': 'v1', 'k2': 'v2'}, {'success': 1000}, {})):
            self.client.types_get(type_id, **kwargs)
            self.assertEqual(
                path4url.mock_calls[-1], call('types', type_id or ''))
            success = kwargs.pop('success', 200)
            self.assertEqual(get.mock_calls[-1], call(
                'path_str', success=success, **kwargs))


if __name__ == '__main__':
    from sys import argv
    from kamaki.clients.test import runTestCase
    not_found = True
    if not argv[1:] or argv[1] == 'BlockStorageRestClient':
        not_found = False
        runTestCase(
            BlockStorageRestClient, 'Block Storage Rest Client', argv[2:])
    if not_found:
        print('TestCase %s not found' % argv[1])
