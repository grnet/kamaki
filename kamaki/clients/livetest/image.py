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

import time

from kamaki.clients import livetest
from kamaki.clients.astakos import AstakosClient as AstakosCachedClient
from kamaki.clients.cyclades import CycladesClient
from kamaki.clients.image import ImageClient
from kamaki.clients import ClientError


IMGMETA = set([
    'id', 'name', 'checksum', 'container-format', 'location', 'disk-format',
    'is-public', 'status', 'deleted-at', 'updated-at', 'created-at', 'owner',
    'size'])


class Image(livetest.Generic):
    def setUp(self):
        self.now = time.mktime(time.gmtime())
        self.cloud = 'cloud.%s' % self['testcloud']
        aurl, self.token = self[self.cloud, 'url'], self[self.cloud, 'token']
        self.auth_base = AstakosCachedClient(aurl, self.token)
        self.imgname = 'img_%s' % self.now
        url = self.auth_base.get_service_endpoints('image')['publicURL']
        self.token = self.auth_base.token
        self.client = ImageClient(url, self.token)
        cyclades_url = self.auth_base.get_service_endpoints(
            'compute')['publicURL']
        self.cyclades = CycladesClient(cyclades_url, self.token)
        self._imglist = {}
        self._imgdetails = {}

    def test_000(self):
        self._prepare_img()
        super(self.__class__, self).test_000()

    def _prepare_img(self):
        f = open(self['image', 'local_path'], 'rb')
        (token, uuid) = (self.token, self.auth_base.user_term('id'))
        purl = self.auth_base.get_service_endpoints(
            'object-store')['publicURL']
        from kamaki.clients.pithos import PithosClient
        self.pithcli = PithosClient(purl, token, uuid)
        cont = 'cont_%s' % self.now
        self.pithcli.container = cont
        self.obj = 'obj_%s' % self.now
        print('\t- Create container %s on Pithos server' % cont)
        self.pithcli.container_put()
        self.location = 'pithos://%s/%s/%s' % (uuid, cont, self.obj)
        print('\t- Upload an image at %s...\n' % self.location)
        self.pithcli.upload_object(self.obj, f)
        print('\t- ok')
        f.close()

        r = self.client.register(
            self.imgname, self.location, params=dict(is_public=True))
        self._imglist[self.imgname] = dict(
            name=r['name'], id=r['id'])
        self._imgdetails[self.imgname] = r

    def tearDown(self):
        for img in self._imglist.values():
            print('\tDeleting image %s' % img['id'])
            self.cyclades.delete_image(img['id'])
        if hasattr(self, 'pithcli'):
            print('\tDeleting container %s' % self.pithcli.container)
            try:
                self.pithcli.del_container(delimiter='/')
                self.pithcli.purge_container()
            except ClientError:
                pass

    def _get_img_by_name(self, name):
        r = self.cyclades.list_images()
        for img in r:
            if img['name'] == name:
                return img
        return None

    def test_list_public(self):
        """Test list_public"""
        self._test_list_public()

    def _test_list_public(self):
        r = self.client.list_public()
        r0 = self.client.list_public(order='-')
        self.assertTrue(len(r) > 0)
        for img in r:
            for term in (
                    'status',
                    'name',
                    'container_format',
                    'disk_format',
                    'id',
                    'size'):
                self.assertTrue(term in img)
        self.assertTrue(r, r0)
        r0.reverse()
        for i, img in enumerate(r):
            self.assert_dicts_are_equal(img, r0[i])
        r1 = self.client.list_public(detail=True)
        for img in r1:
            for term in (
                    'status',
                    'name',
                    'checksum',
                    'created_at',
                    'disk_format',
                    'updated_at',
                    'id',
                    'location',
                    'container_format',
                    'owner',
                    'is_public',
                    'deleted_at',
                    'properties',
                    'size'):
                self.assertTrue(term in img)
                if len(img['properties']):
                    for interm in ('osfamily', 'root_partition'):
                        self.assertTrue(interm in img['properties'])
        size_max = 1000000000000
        r2 = self.client.list_public(filters=dict(size_max=size_max))
        self.assertTrue(len(r2) <= len(r))
        for img in r2:
            self.assertTrue(int(img['size']) <= size_max)

    def test_get_meta(self):
        """Test get_meta"""
        self._test_get_meta()

    def _test_get_meta(self):
        r = self.client.get_meta(self['image', 'id'])
        self.assertEqual(r['id'], self['image', 'id'])
        for term in (
                'status',
                'name',
                'checksum',
                'updated-at',
                'created-at',
                'deleted-at',
                'location',
                'is-public',
                'owner',
                'disk-format',
                'size',
                'container-format'):
            self.assertTrue(term in r)
            for interm in (
                    'OSFAMILY',
                    'USERS',
                    'ROOT_PARTITION',
                    'OS',
                    'DESCRIPTION'):
                self.assertTrue(interm in r['properties'])

    def test_register(self):
        """Test register"""
        self._prepare_img()
        self._test_register()

    def _test_register(self):
        self.assertTrue(self._imglist)
        for img in self._imglist.values():
            self.assertTrue(img is not None)
            r = set(self._imgdetails[img['name']].keys())
            self.assertTrue(r.issubset(IMGMETA.union(['properties'])))

    def test_unregister(self):
        """Test unregister"""
        self._prepare_img()
        self._test_unregister()

    def _test_unregister(self):
        try:
            for img in self._imglist.values():
                self.client.unregister(img['id'])
                self._prepare_img()
                break
        except ClientError as ce:
            if ce.status in (405,):
                print 'IMAGE UNREGISTER is not supported by server: %s' % ce
            else:
                raise

    def test_set_members(self):
        """Test set_members"""
        self._prepare_img()
        self._test_set_members()

    def _test_set_members(self):
        members = ['%s@fake.net' % self.now]
        for img in self._imglist.values():
            self.client.set_members(img['id'], members)
            r = self.client.list_members(img['id'])
            self.assertEqual(r[0]['member_id'], members[0])

    def test_list_members(self):
        """Test list_members"""
        self._test_list_members()

    def _test_list_members(self):
        self._test_set_members()

    def test_remove_members(self):
        """Test remove_members - NO CHECK"""
        self._prepare_img()
        self._test_remove_members()

    def _test_remove_members(self):
        return
        members = ['%s@fake.net' % self.now, '%s_v2@fake.net' % self.now]
        for img in self._imglist.values():
            self.client.set_members(img['id'], members)
            r = self.client.list_members(img['id'])
            self.assertTrue(len(r) > 1)
            self.client.remove_member(img['id'], members[0])
            r0 = self.client.list_members(img['id'])
            self.assertEqual(len(r), 1 + len(r0))
            self.assertEqual(r0[0]['member_id'], members[1])

    def test_list_shared(self):
        """Test list_shared - NOT CHECKED"""
        self._test_list_shared()

    def _test_list_shared(self):
        #No way to test this, if I dont have member images
        pass
