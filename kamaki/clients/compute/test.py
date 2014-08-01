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
from json import dumps
from sys import stdout
import json

from kamaki.clients import ClientError, compute


rest_pkg = 'kamaki.clients.compute.rest_api.ComputeRestClient'
compute_pkg = 'kamaki.clients.compute.ComputeClient'

img_ref = "1m4g3-r3f3r3nc3"
vm_name = "my new VM"
fid = 42
vm_send = dict(server=dict(
    flavorRef=fid,
    name=vm_name,
    imageRef=img_ref,
    metadata=dict(os="debian", users="root")))
vm_recv = dict(server=dict(
    status="BUILD",
    updated="2013-03-01T10:04:00.637152+00:00",
    hostId="",
    name=vm_name,
    imageRef=img_ref,
    created="2013-03-01T10:04:00.087324+00:00",
    flavorRef=fid,
    adminPass="n0n3sh@11p@55",
    suspended=False,
    progress=0,
    id=31173,
    metadata=dict(os="debian", users="root")))
img_recv = dict(image=dict(
    status="ACTIVE",
    updated="2013-02-26T11:10:14+00:00",
    name="Debian Base",
    created="2013-02-26T11:03:29+00:00",
    progress=100,
    id=img_ref,
    metadata=dict(
        partition_table="msdos",
        kernel="2.6.32",
        osfamily="linux",
        users="root",
        gui="No GUI",
        sortorder="1",
        os="debian",
        root_partition="1",
        description="Debian 6.0.7 (Squeeze) Base System")))
vm_list = dict(servers=[
    dict(name='n1', id=1),
    dict(name='n2', id=2)])
flavor_list = dict(flavors=[
    dict(id=41, name="C1R1024D20"),
    dict(id=42, name="C1R1024D40"),
    dict(id=43, name="C1R1028D20")])
img_list = dict(images=[
    dict(name="maelstrom", id="0fb03e45-7d5a-4515-bd4e-e6bbf6457f06"),
    dict(name="edx_saas", id="1357163d-5fd8-488e-a117-48734c526206"),
    dict(name="Debian_Wheezy_Base", id="1f8454f0-8e3e-4b6c-ab8e-5236b728dffe"),
    dict(name="CentOS", id="21894b48-c805-4568-ac8b-7d4bb8eb533d"),
    dict(name="Ubuntu Desktop", id="37bc522c-c479-4085-bfb9-464f9b9e2e31"),
    dict(name="Ubuntu 12.10", id="3a24fef9-1a8c-47d1-8f11-e07bd5e544fd"),
    dict(name="Debian Base", id="40ace203-6254-4e17-a5cb-518d55418a7d"),
    dict(name="ubuntu_bundled", id="5336e265-5c7c-4127-95cb-2bf832a79903")])


class FR(object):
    """FR stands for Fake Response"""
    json = vm_recv
    headers = {}
    content = json
    status = None
    status_code = 200


def print_iterations(old, new):
    if new:
        if new % 1000:
            return old
        stdout.write('\b' * len('%s' % old))
        stdout.write('%s' % new)
    else:
        stdout.write('# of loops:  ')
    stdout.flush()
    return new


class ComputeRestClient(TestCase):

    """Set up a ComputesRest thorough test"""
    def setUp(self):
        self.url = 'http://cyclades.example.com'
        self.token = 'cyc14d3s70k3n'
        self.client = compute.ComputeRestClient(self.url, self.token)

    def tearDown(self):
        FR.json = vm_recv

    @patch('%s.set_param' % rest_pkg)
    @patch('%s.get' % rest_pkg, return_value=FR())
    def _test_get(self, service, params, get, set_param):
        method = getattr(self.client, '%s_get' % service)
        param_args = [({}, {k: k}, {k: v[1]}) for k, v in params.items()]
        num_of_its = 0
        for i, args in enumerate(product(
                ('', '%s_id' % service),
                (None, False, True),
                (200, 204),
                ({}, {'k': 'v'}),
                *param_args)):
            (srv_id, detail, success, kwargs) = args[:4]
            kwargs['success'] = success
            srv_kwargs = dict()
            for param in args[4:]:
                srv_kwargs.update(param)
            srv_kwargs.update(kwargs)
            method(*args[:2], **srv_kwargs)
            srv_str = '/detail' if detail else (
                '/%s' % srv_id) if srv_id else ''
            self.assertEqual(
                get.mock_calls[-1],
                call('/%s%s' % (service, srv_str), **kwargs))
            param_calls = []
            for k, v in params.items():
                real_v = srv_kwargs.get(k, v[1]) if not srv_id else v[1]
                param_calls.append(call(v[0], real_v, iff=real_v))
            actual = set_param.mock_calls[- len(param_calls):]
            self.assertEqual(sorted(actual), sorted(param_calls))

            num_of_its = print_iterations(num_of_its, i)
        print ('\b' * len('%s' % num_of_its)) + ('%s' % i)

    @patch('%s.set_param' % rest_pkg)
    @patch('%s.get' % rest_pkg, return_value=FR())
    def _test_srv_cmd_get(self, srv, cmd, params, get, set_param):
        method = getattr(self.client, '%s_%s_get' % (srv, cmd))
        param_args = [({}, {k: k}, {k: v[1]}) for k, v in params.items()]
        num_of_its = 0
        for i, args in enumerate(product(
                ('some_server_id', 'other_server_id'),
                (None, 'xtra_id'),
                ((304, 200), (1000)),
                ({}, {'k': 'v'}),
                *param_args)):
            srv_id, xtra_id, success, kwargs = args[:4]
            kwargs = dict(kwargs)
            kwargs['success'] = success
            srv_kwargs = dict()
            for param in args[4:]:
                srv_kwargs.update(param)
            srv_kwargs.update(kwargs)
            method(*args[:2], **srv_kwargs)
            srv_str = '/%s/%s/%s' % (srv, srv_id, cmd)
            srv_str += ('/%s' % xtra_id) if xtra_id else ''
            self.assertEqual(get.mock_calls[-1], call(srv_str, **kwargs))
            param_calls = []
            for k, v in params.items():
                real_v = srv_kwargs.get(k, v[1])
                param_calls.append(call(v[0], real_v, iff=real_v))
            actual = set_param.mock_calls[- len(param_calls):]
            self.assertEqual(sorted(actual), sorted(param_calls))

            num_of_its = print_iterations(num_of_its, i)
        print ('\b' * len('%s' % num_of_its)) + ('%s' % i)

    @patch('%s.set_header' % rest_pkg)
    @patch('%s.set_param' % rest_pkg)
    @patch('%s.post' % rest_pkg, return_value=FR())
    def _test_post(self, srv, cmd, params, post, set_param, set_header):
        method = getattr(
            self.client, '%s_%spost' % (srv, ('%s_' % cmd) if cmd else ''))
        param_args = [({}, {k: k}, {k: v[1]}) for k, v in params.items()]
        num_of_its = 0
        for i, args in enumerate(product(
                ('%s_id' % srv, 'some_value'),
                (
                    None,
                    {'some': {'data': 'in json'}},
                    ['k1', {'k2': 'v2', 'k3': 'v3'}, 'k4']),
                (202, 1453),
                ({}, {'k': 'v'}),
                *param_args)):
            srv_id, json_data, success, kwargs = args[:4]
            kwargs = dict(kwargs)
            cmd_args = (srv_id, ) if cmd else ()
            kwargs['success'] = success
            srv_kwargs = dict()
            for param in args[4:]:
                srv_kwargs.update(param)
            srv_kwargs.update(kwargs)
            srv_kwargs['json_data'] = json_data
            method(*cmd_args, **srv_kwargs)
            srv_str = '/%s%s' % (
                srv, (('/%s/%s' % (srv_id, cmd)) if cmd else ''))
            kwargs['data'] = json.dumps(json_data) if json_data else None
            self.assertEqual(post.mock_calls[-1], call(srv_str, **kwargs))

            param_calls = []
            for k, v in params.items():
                real_v = srv_kwargs.get(k, v[1])
                param_calls.append(call(v[0], real_v, iff=real_v))
            actual = set_param.mock_calls[- len(param_calls):]
            self.assertEqual(sorted(actual), sorted(param_calls))

            if json_data:
                self.assertEqual(set_header.mock_calls[-2:], [
                    call('Content-Type', 'application/json'),
                    call('Content-Length', len(kwargs['data']))])

            num_of_its = print_iterations(num_of_its, i)
        print ('\b' * len('%s' % num_of_its)) + ('%s' % i)

    @patch('%s.set_header' % rest_pkg)
    @patch('%s.set_param' % rest_pkg)
    @patch('%s.put' % rest_pkg, return_value=FR())
    def _test_put(self, srv, cmd, params, put, set_param, set_headers):
        method = getattr(self.client, '%s_%sput' % (
            srv, ('%s_' % cmd) if cmd else ''))
        param_args = [({}, {k: k}, {k: v[1]}) for k, v in params.items()]
        num_of_its = 0
        for i, args in enumerate(product(
                ('some_value', '%s_id' % srv),
                (None, [dict(json="data"), dict(data="json")]),
                (204, 504),
                ({}, {'k': 'v'}),
                *param_args)):
            srv_id, json_data, success, kwargs = args[:4]
            kwargs = dict(kwargs)
            kwargs['success'] = success
            srv_kwargs = dict()
            for param in args[4:]:
                srv_kwargs.update(param)
            srv_kwargs.update(kwargs)
            srv_kwargs['json_data'] = json_data
            method(srv_id, **srv_kwargs)
            srv_str = '/%s/%s%s' % (srv, srv_id, ('/%s' % cmd if cmd else ''))

            if json_data:
                json_data = dumps(json_data)
                self.assertEqual(set_headers.mock_calls[-2:], [
                    call('Content-Type', 'application/json'),
                    call('Content-Length', len(json_data))])
            self.assertEqual(
                put.mock_calls[-1],
                call(srv_str, data=json_data, **kwargs))

            param_calls = []
            for k, v in params.items():
                real_v = srv_kwargs.get(k, v[1])
                param_calls.append(call(v[0], real_v, iff=real_v))
            actual = set_param.mock_calls[- len(param_calls):]
            self.assertEqual(sorted(actual), sorted(param_calls))

            num_of_its = print_iterations(num_of_its, i)
        print ('\b' * len('%s' % num_of_its)) + ('%s' % i)

    @patch('%s.delete' % rest_pkg, return_value=FR())
    def _test_delete(self, srv, cmd, delete):
        method = getattr(
            self.client, '%s_%sdelete' % (srv, ('%s_' % cmd) if cmd else ''))
        cmd_params = ('some_cmd_value', 'some_other_value') if cmd else ()
        num_of_its = 0
        for i, args in enumerate(product(
                ('%s_id' % srv, 'some_value'),
                (204, 208),
                ({}, {'k': 'v'}),
                *cmd_params)):
            (srv_id, success, kwargs) = args[:3]
            kwargs = dict(kwargs)
            kwargs['success'] = success
            cmd_value = args[-1] if cmd else ''
            method_args = (srv_id, cmd_value) if cmd else (srv_id, )
            method(*method_args, **kwargs)
            srv_str = '/%s/%s' % (srv, srv_id)
            cmd_str = ('/%s/%s' % (cmd, cmd_value)) if cmd else ''
            self.assertEqual(
                delete.mock_calls[-1],
                call('%s%s' % (srv_str, cmd_str), **kwargs))
            num_of_its = print_iterations(num_of_its, i)
        print ('\b' * len('%s' % num_of_its)) + ('%s' % i)

    @patch('%s.get' % rest_pkg, return_value=FR())
    def test_limits_get(self, get):
        self.client.limits_get(success='some_val')
        get.assert_called_once_with('/limits', success='some_val')

    def test_servers_get(self):
        params = dict(
            changes_since=('changes-since', None),
            image=('image', None),
            flavor=('flavor', None),
            name=('name', None),
            marker=('marker', None),
            limit=('limit', None),
            status=('status', None),
            host=('host', None))
        self._test_get('servers', params)

    def test_servers_post(self):
        params = dict(
            security_group=('security_group', None),
            user_data=('user_data', None),
            availability_zone=('availability_zone', None))
        self._test_post('servers', None, params)

    def test_servers_put(self):
        self._test_put('servers', None, dict(server_name=('server', None)))

    def test_servers_delete(self):
        self._test_delete('servers', None)

    def test_servers_metadata_get(self):
        self._test_srv_cmd_get('servers', 'metadata', {})

    def test_servers_metadata_post(self):
        self._test_post('servers', 'metadata', {})

    def test_servers_metadata_put(self):
        self._test_put('servers', 'metadata', {})

    def test_images_metadata_delete(self):
        self._test_delete('images', 'metadata')

    def test_servers_action_post(self):
        self._test_post('servers', 'action', {})

    def test_servers_ips_get(self):
        params = dict(changes_since=('changes-since', None))
        self._test_srv_cmd_get('servers', 'ips', params)

    def test_images_get(self):
        param = dict(
            changes_since=('changes-since', None),
            server_name=('server', None),
            name=('name', None),
            status=('status', None),
            marker=('marker', None),
            limit=('limit', None),
            type=('type', None))
        self._test_get('images', param)

    def test_images_delete(self):
        self._test_delete('images', None)

    def test_images_metadata_get(self):
        self._test_srv_cmd_get('images', 'metadata', {})

    def test_images_metadata_post(self):
        self._test_post('images', 'metadata', {})

    def test_images_metadata_put(self):
        self._test_put('images', 'metadata', {})

    def test_servers_metadata_delete(self):
        self._test_delete('servers', 'metadata')

    def test_flavors_get(self):
        params = dict(
            changes_since=('changes-since', None),
            minDisk=('minDisk', None),
            minRam=('minRam', None),
            marker=('marker', None),
            limit=('limit', None))
        self._test_get('flavors', params)

    @patch('%s.get' % rest_pkg, return_value=FR())
    def test_floating_ip_pools_get(self, get):
        for args in product(
                (200, 204),
                ({}, {'k': 'v'})):
            success, kwargs = args
            r = self.client.floating_ip_pools_get(success, **kwargs)
            self.assertTrue(isinstance(r, FR))
            self.assertEqual(get.mock_calls[-1], call(
                '/os-floating-ip-pools', success=success, **kwargs))

    @patch('%s.get' % rest_pkg, return_value=FR())
    def test_floating_ips_get(self, get):
        for args in product(
                ('', '192.193.194.195'),
                (200, 204),
                ({}, {'k': 'v'})):
            ip, success, kwargs = args
            r = self.client.floating_ips_get(*args[:2], **kwargs)
            self.assertTrue(isinstance(r, FR))
            expected = '' if not ip else '/%s' % ip
            self.assertEqual(get.mock_calls[-1], call(
                '/os-floating-ips%s' % expected, success=success, **kwargs))

    @patch('%s.post' % rest_pkg, return_value=FR())
    def test_floating_ips_post(self, post):
        for args in product(
                (None, [dict(json='data'), dict(data='json')]),
                ('', '192.193.194.195'),
                (202, 204),
                ({}, {'k': 'v'})):
            json_data, ip, success, kwargs = args
            self.client.floating_ips_post(*args[:3], **kwargs)
            expected = '' if not ip else '/%s' % ip
            self.assertEqual(post.mock_calls[-1], call(
                '/os-floating-ips%s' % expected,
                json=json_data, success=success,
                **kwargs))

    @patch('%s.delete' % rest_pkg, return_value=FR())
    def test_floating_ips_delete(self, delete):
        for args in product(
                ('', '192.193.194.195'),
                (204,),
                ({}, {'k': 'v'})):
            ip, success, kwargs = args
            r = self.client.floating_ips_delete(*args[:2], **kwargs)
            self.assertTrue(isinstance(r, FR))
            expected = '' if not ip else '/%s' % ip
            self.assertEqual(delete.mock_calls[-1], call(
                '/os-floating-ips%s' % expected, success=success, **kwargs))


class ComputeClient(TestCase):

    def assert_dicts_are_equal(self, d1, d2):
        for k, v in d1.items():
            self.assertTrue(k in d2)
            if isinstance(v, dict):
                self.assert_dicts_are_equal(v, d2[k])
            else:
                self.assertEqual(unicode(v), unicode(d2[k]))

    """Set up a Cyclades thorough test"""
    def setUp(self):
        self.url = 'http://cyclades.example.com'
        self.token = 'cyc14d3s70k3n'
        self.client = compute.ComputeClient(self.url, self.token)

    def tearDown(self):
        FR.status_code = 200
        FR.json = vm_recv

    def test_create_server(self):
        with patch.object(
                compute.ComputeClient, 'servers_post',
                side_effect=ClientError(
                    'REQUEST ENTITY TOO LARGE',
                    status=403)):
            self.assertRaises(
                ClientError,
                self.client.create_server,
                vm_name, fid, img_ref)

        for params in product(
                ('security_group', None),
                ('user_data', None),
                ('availability_zone', None),
                (None, {'os': 'debian', 'users': 'root'})):
            kwargs = dict()
            for i, k in enumerate((
                    'security_group', 'user_data', 'availability_zone')):
                if params[i]:
                    kwargs[k] = params[i]
            with patch.object(
                    compute.ComputeClient, 'servers_post',
                    return_value=FR()) as post:
                r = self.client.create_server(vm_name, fid, img_ref, **kwargs)
                self.assertEqual(r, FR.json['server'])
                exp_json = dict(server=dict(
                    flavorRef=fid, name=vm_name, imageRef=img_ref))
                for k in set([
                        'security_group',
                        'user_data',
                        'availability_zone']).difference(kwargs):
                    kwargs[k] = None
                self.assertEqual(
                    post.mock_calls[-1], call(json_data=exp_json, **kwargs))
                prsn = 'Personality string (does not work with real servers)'
                self.client.create_server(
                    vm_name, fid, img_ref, personality=prsn, **kwargs)
                exp_json['server']['personality'] = prsn
                self.assertEqual(
                    post.mock_calls[-1], call(json_data=exp_json, **kwargs))
                kwargs.pop('personality', None)
                exp_json['server'].pop('personality', None)
                mtdt = 'Metadata dict here'
                self.client.create_server(
                    vm_name, fid, img_ref, metadata=mtdt, **kwargs)
                exp_json['server']['metadata'] = mtdt
                self.assertEqual(
                    post.mock_calls[-1], call(json_data=exp_json, **kwargs))

    @patch('%s.servers_get' % compute_pkg, return_value=FR())
    def test_list_servers(self, SG):
        FR.json = vm_list
        for args in product(
                (False, True),
                ({}, dict(status='status')),
                ({}, dict(name='name')),
                ({}, dict(image='image')),
                ({}, dict(flavor='flavor')),
                ({}, dict(host='host')),
                ({}, dict(limit='limit')),
                ({}, dict(marker='marker')),
                ({}, dict(changes_since='changes_since'))):
            detail = args[0]
            kwargs = dict()
            for param in args[1:]:
                kwargs.update(param)
            r = self.client.list_servers(detail, **kwargs)
            for k in set([
                    'status', 'name',
                    'image', 'flavor',
                    'host', 'limit',
                    'marker', 'changes_since']).difference(kwargs):
                kwargs[k] = None
            self.assertEqual(SG.mock_calls[-1], call(detail=detail, **kwargs))
            for i, vm in enumerate(vm_list['servers']):
                self.assert_dicts_are_equal(r[i], vm)
            self.assertEqual(i + 1, len(r))

    @patch('%s.servers_get' % compute_pkg, return_value=FR())
    def test_get_server_details(self, SG):
        vm_id = vm_recv['server']['id']
        for args in product(
                ({}, dict(status='status')),
                ({}, dict(name='name')),
                ({}, dict(image='image')),
                ({}, dict(flavor='flavor')),
                ({}, dict(host='host')),
                ({}, dict(limit='limit')),
                ({}, dict(marker='marker')),
                ({}, dict(changes_since='changes_since'))):
            kwargs = dict()
            for param in args:
                kwargs.update(param)
            r = self.client.get_server_details(vm_id, **kwargs)
            for k in set([
                    'status', 'name',
                    'image', 'flavor',
                    'host', 'limit',
                    'marker', 'changes_since']).difference(kwargs):
                kwargs[k] = None
            self.assertEqual(SG.mock_calls[-1], call(vm_id, **kwargs))
            self.assert_dicts_are_equal(r, vm_recv['server'])

    @patch('%s.servers_put' % compute_pkg, return_value=FR())
    def test_update_server_name(self, SP):
        vm_id = vm_recv['server']['id']
        new_name = vm_name + '_new'
        self.client.update_server_name(vm_id, new_name)
        SP.assert_called_once_with(vm_id, json_data=dict(
            server=dict(name=new_name)))

    @patch('%s.servers_action_post' % compute_pkg, return_value=FR())
    def test_reboot_server(self, SP):
        vm_id = vm_recv['server']['id']
        for hard in (None, True):
            self.client.reboot_server(vm_id, hard=hard)
            self.assertEqual(SP.mock_calls[-1], call(vm_id, json_data=dict(
                reboot=dict(type='HARD' if hard else 'SOFT'))))

    @patch('%s.servers_action_post' % compute_pkg, return_value=FR())
    def test_resize_server(self, SP):
        vm_id, flavor = vm_recv['server']['id'], flavor_list['flavors'][1]
        self.client.resize_server(vm_id, flavor['id'])
        exp = dict(resize=dict(flavorRef=flavor['id']))
        SP.assert_called_once_with(vm_id, json_data=exp)

    @patch('%s.servers_metadata_put' % compute_pkg, return_value=FR())
    def test_create_server_metadata(self, SP):
        vm_id = vm_recv['server']['id']
        metadata = dict(m1='v1', m2='v2', m3='v3')
        FR.json = dict(meta=vm_recv['server'])
        for k, v in metadata.items():
            r = self.client.create_server_metadata(vm_id, k, v)
            self.assert_dicts_are_equal(r, vm_recv['server'])
            self.assertEqual(SP.mock_calls[-1], call(
                vm_id, '%s' % k,
                json_data=dict(meta={k: v}), success=201))

    @patch('%s.servers_metadata_get' % compute_pkg, return_value=FR())
    def test_get_server_metadata(self, SG):
        vm_id = vm_recv['server']['id']
        metadata = dict(m1='v1', m2='v2', m3='v3')
        FR.json = dict(metadata=metadata)
        r = self.client.get_server_metadata(vm_id)
        FR.json = dict(meta=metadata)
        SG.assert_called_once_with(vm_id, '')
        self.assert_dicts_are_equal(r, metadata)

        for k, v in metadata.items():
            FR.json = dict(meta={k: v})
            r = self.client.get_server_metadata(vm_id, k)
            self.assert_dicts_are_equal(r, {k: v})
            self.assertEqual(
                SG.mock_calls[-1], call(vm_id, '%s' % k))

    @patch('%s.servers_metadata_post' % compute_pkg, return_value=FR())
    def test_update_server_metadata(self, SP):
        vm_id = vm_recv['server']['id']
        metadata = dict(m1='v1', m2='v2', m3='v3')
        FR.json = dict(metadata=metadata)
        r = self.client.update_server_metadata(vm_id, **metadata)
        self.assert_dicts_are_equal(r, metadata)
        SP.assert_called_once_with(
            vm_id, json_data=dict(metadata=metadata), success=201)

    @patch('%s.servers_metadata_delete' % compute_pkg, return_value=FR())
    def test_delete_server_metadata(self, SD):
        vm_id = vm_recv['server']['id']
        key = 'metakey'
        self.client.delete_server_metadata(vm_id, key)
        SD.assert_called_once_with(vm_id, key)

    @patch('%s.flavors_get' % compute_pkg, return_value=FR())
    def test_list_flavors(self, FG):
        FR.json = flavor_list
        for detail in ('', 'detail'):
            r = self.client.list_flavors(detail=bool(detail))
            self.assertEqual(FG.mock_calls[-1], call(detail=bool(detail)))
            self.assertEqual(r, flavor_list['flavors'])

    @patch('%s.flavors_get' % compute_pkg, return_value=FR())
    def test_get_flavor_details(self, FG):
        FR.json = dict(flavor=flavor_list['flavors'][0])
        r = self.client.get_flavor_details(fid)
        FG.assert_called_once_with(fid)
        self.assert_dicts_are_equal(r, flavor_list['flavors'][0])

    @patch('%s.images_get' % compute_pkg, return_value=FR())
    def test_list_images(self, IG):
        FR.json = img_list
        for detail in ('', 'detail'):
            r = self.client.list_images(detail=detail)
            self.assertEqual(IG.mock_calls[-1], call(detail=bool(detail)))
            expected = img_list['images']
            for i in range(len(r)):
                self.assert_dicts_are_equal(expected[i], r[i])

    @patch('%s.images_get' % compute_pkg, return_value=FR())
    def test_get_image_details(self, IG):
        FR.json = img_recv
        r = self.client.get_image_details(img_ref)
        IG.assert_called_once_with(img_ref)
        self.assert_dicts_are_equal(r, img_recv['image'])

    @patch('%s.images_metadata_get' % compute_pkg, return_value=FR())
    def test_get_image_metadata(self, IG):
        for key in ('', '50m3k3y'):
            FR.json = dict(meta=img_recv['image']) if (
                key) else dict(metadata=img_recv['image'])
            r = self.client.get_image_metadata(img_ref, key)
            self.assertEqual(IG.mock_calls[-1], call(img_ref, key or ''))
            self.assert_dicts_are_equal(img_recv['image'], r)

    @patch('%s.servers_delete' % compute_pkg, return_value=FR())
    def test_delete_server(self, SD):
        vm_id = vm_recv['server']['id']
        self.client.delete_server(vm_id)
        SD.assert_called_once_with(vm_id)

    @patch('%s.images_delete' % compute_pkg, return_value=FR())
    def test_delete_image(self, ID):
        self.client.delete_image(img_ref)
        ID.assert_called_once_with(img_ref)

    # @patch('%s.images_metadata_put' % compute_pkg, return_value=FR())
    # def test_create_image_metadata(self, IP):
    #     (key, val) = ('k1', 'v1')
    #     FR.json = dict(meta=img_recv['image'])
    #     r = self.client.create_image_metadata(img_ref, key, val)
    #     IP.assert_called_once_with(
    #         img_ref, '%s' % key,
    #         json_data=dict(meta={key: val}))
    #     self.assert_dicts_are_equal(r, img_recv['image'])

    @patch('%s.images_metadata_post' % compute_pkg, return_value=FR())
    def test_update_image_metadata(self, IP):
        metadata = dict(m1='v1', m2='v2', m3='v3')
        FR.json = dict(metadata=metadata)
        r = self.client.update_image_metadata(img_ref, **metadata)
        IP.assert_called_once_with(
            img_ref, json_data=dict(metadata=metadata))
        self.assert_dicts_are_equal(r, metadata)

    @patch('%s.images_metadata_delete' % compute_pkg, return_value=FR())
    def test_delete_image_metadata(self, ID):
        key = 'metakey'
        self.client.delete_image_metadata(img_ref, key)
        ID.assert_called_once_with(img_ref, '%s' % key)

    @patch('%s.floating_ip_pools_get' % compute_pkg, return_value=FR())
    def test_get_floating_ip_pools(self, get):
        tid = 't3n@nt_1d'
        r = self.client.get_floating_ip_pools(tid)
        self.assert_dicts_are_equal(r, FR.json)
        self.assertEqual(get.mock_calls[-1], call(tid))

    @patch('%s.floating_ips_get' % compute_pkg, return_value=FR())
    def test_get_floating_ips(self, get):
        tid = 't3n@nt_1d'
        r = self.client.get_floating_ips(tid)
        self.assert_dicts_are_equal(r, FR.json)
        self.assertEqual(get.mock_calls[-1], call(tid))

    @patch('%s.floating_ips_post' % compute_pkg, return_value=FR())
    def test_alloc_floating_ip(self, post):
        FR.json = dict(floating_ip=dict(
            fixed_ip='fip',
            id=1,
            instance_id='lala',
            ip='102.0.0.1',
            pool='pisine'))
        for args in product(
                ('t1', 't2'),
                (None, 'pisine')):
            r = self.client.alloc_floating_ip(*args)
            tenant_id, pool = args
            self.assert_dicts_are_equal(r, FR.json['floating_ip'])
            expected = dict(pool=pool) if pool else dict()
            self.assertEqual(post.mock_calls[-1], call(tenant_id, expected))

    @patch('%s.floating_ips_get' % compute_pkg, return_value=FR())
    def test_get_floating_ip(self, get):
        FR.json = dict(floating_ips=[dict(
            fixed_ip='fip',
            id=1,
            instance_id='lala',
            ip='102.0.0.1',
            pool='pisine'), ])
        for args in product(
                ('t1', 't2'),
                (None, 'fip')):
            r = self.client.get_floating_ip(*args)
            tenant_id, fip = args
            self.assertEqual(r, FR.json['floating_ips'])
            self.assertEqual(get.mock_calls[-1], call(tenant_id, fip))

    @patch('%s.floating_ips_delete' % compute_pkg, return_value=FR())
    def test_delete_floating_ip(self, delete):
        for args in product(
                ('t1', 't2'),
                (None, 'fip')):
            r = self.client.delete_floating_ip(*args)
            tenant_id, fip = args
            self.assertEqual(r, FR.headers)
            self.assertEqual(delete.mock_calls[-1], call(tenant_id, fip))


if __name__ == '__main__':
    from sys import argv
    from kamaki.clients.test import runTestCase
    not_found = True
    if not argv[1:] or argv[1] == 'ComputeClient':
        not_found = False
        runTestCase(ComputeClient, 'Compute Client', argv[2:])
    if not argv[1:] or argv[1] == 'ComputeRest':
        not_found = False
        runTestCase(ComputeRestClient, 'ComputeRest Client', argv[2:])
    if not_found:
        print('TestCase %s not found' % argv[1])
