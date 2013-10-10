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
import datetime
from os import urandom
from tempfile import NamedTemporaryFile
from string import ascii_letters

from kamaki.clients import livetest, ClientError
from kamaki.clients.pithos import PithosClient
from kamaki.clients.astakos import AstakosClient


def chargen():
    """10 + 2 * 26 + 26 = 88"""
    while True:
        for CH in xrange(10):
            yield '%s' % CH
        for CH in ascii_letters:
            yield CH
        for CH in '~!@#$%^&*()_+`-=:";|<>?,./':
            yield CH


def sample_block(f, block):
    block_size = 4 * 1024 * 1024
    f.seek(block * block_size)
    ch = [f.read(1)]
    f.seek(block_size / 2, 1)
    ch.append(f.read(1))
    f.seek((block + 1) * block_size - 1)
    ch.append(f.read(1))
    return ch


class Pithos(livetest.Generic):

    files = []

    def setUp(self):
        self.cloud = 'cloud.%s' % self['testcloud']
        aurl, self.token = self[self.cloud, 'url'], self[self.cloud, 'token']
        self.auth_base = AstakosClient(aurl, self.token)
        purl = self.auth_base.get_service_endpoints(
            'object-store')['publicURL']
        self.uuid = self.auth_base.user_term('id')
        self.client = PithosClient(purl, self.token, self.uuid)

        self.now = time.mktime(time.gmtime())
        self.now_unformated = datetime.datetime.utcnow()
        self._init_data()

        """Prepare an object to be shared - also its container"""
        self.client.container = self.c1
        self.client.object_post(
            'test',
            update=True,
            permissions={'read': [self.client.account]})

        self.create_remote_object(self.c1, 'another.test')

    def _init_data(self):
        self.c1 = 'c1_' + unicode(self.now)
        self.c2 = 'c2_' + unicode(self.now)
        self.c3 = 'c3_' + unicode(self.now)
        try:
            self.client.create_container(self.c2)
        except ClientError:
            pass
        try:
            self.client.create_container(self.c1)
        except ClientError:
            pass
        try:
            self.client.create_container(self.c3)
        except ClientError:
            pass

        self.create_remote_object(self.c1, 'test')
        self.create_remote_object(self.c2, 'test')
        self.create_remote_object(self.c1, 'test1')
        self.create_remote_object(self.c2, 'test1')

    def create_remote_object(self, container, obj):
        self.client.container = container
        self.client.object_put(
            obj,
            content_type='application/octet-stream',
            data='file %s that lives in %s' % (obj, container),
            metadata={'incontainer': container})

    def forceDeleteContainer(self, container):
        self.client.container = container
        try:
            r = self.client.list_objects()
        except ClientError:
            return
        for obj in r:
            name = obj['name']
            self.client.del_object(name)
        r = self.client.container_delete()
        self.container = ''

    def tearDown(self):
        """Destroy test cases"""
        for f in self.files:
            f.close()
        self.forceDeleteContainer(self.c1)
        self.forceDeleteContainer(self.c2)
        try:
            self.forceDeleteContainer(self.c3)
        except ClientError:
            pass
        self.client.container = ''

    def test_000(self):
        """Prepare a full Pithos+ test"""
        print('')
        super(self.__class__, self).test_000()

    def test_account_head(self):
        """Test account_HEAD"""
        self._test_0010_account_head()

    def _test_0010_account_head(self):
        r = self.client.account_head()
        self.assertEqual(r.status_code, 204)

        r = self.client.account_head(until='1000000000')
        self.assertEqual(r.status_code, 204)

        r = self.client.get_account_info(until='1000000000')
        datestring = unicode(r['x-account-until-timestamp'])
        self.assertEqual(u'Sun, 09 Sep 2001 01:46:40 GMT', datestring)

        r = self.client.get_account_quota()
        self.assertTrue('x-account-policy-quota' in r)

        #r = self.client.get_account_versioning()
        #self.assertTrue('x-account-policy-versioning' in r)

        """Check if(un)modified_since"""
        for format in self.client.DATE_FORMATS:
            now_formated = self.now_unformated.strftime(format)
            r1 = self.client.account_head(
                if_modified_since=now_formated, success=(204, 304, 412))
            sc1 = r1.status_code
            r2 = self.client.account_head(
                if_unmodified_since=now_formated, success=(204, 304, 412))
            sc2 = r2.status_code
            self.assertNotEqual(sc1, sc2)

    def test_account_get(self):
        """Test account_GET"""
        self._test_0020_account_get()

    def _test_0020_account_get(self):
        #r = self.client.account_get()
        #self.assertEqual(r.status_code, 200)
        r = self.client.list_containers()
        fullLen = len(r)
        self.assertTrue(fullLen > 2)

        r = self.client.account_get(limit=1)
        self.assertEqual(len(r.json), 1)

        r = self.client.account_get(marker='c2_')
        temp_c0 = r.json[0]['name']
        temp_c2 = r.json[2]['name']

        r = self.client.account_get(limit=2, marker='c2_')
        conames = [container['name'] for container in r.json if (
            container['name'].lower().startswith('c2_'))]
        self.assertTrue(temp_c0 in conames)
        self.assertFalse(temp_c2 in conames)

        r = self.client.account_get(show_only_shared=True)
        self.assertTrue(self.c1 in [c['name'] for c in r.json])

        r = self.client.account_get(until=1342609206.0)
        self.assertTrue(len(r.json) <= fullLen)

        """Check if(un)modified_since"""
        for format in self.client.DATE_FORMATS:
            now_formated = self.now_unformated.strftime(format)
            r1 = self.client.account_get(
                if_modified_since=now_formated, success=(200, 304, 412))
            sc1 = r1.status_code
            r2 = self.client.account_get(
                if_unmodified_since=now_formated, success=(200, 304, 412))
            sc2 = r2.status_code
            self.assertNotEqual(sc1, sc2)

        """Check sharing_accounts"""
        r = self.client.get_sharing_accounts()
        try:
            self.assertTrue(len(r) > 0)
        except AssertionError as e:
            print '\n\tWARNING: Are there any sharers to your account?'
            self.assertEqual(len(r), 0)
            print '\tIf there are, this (%s) is an error, else it is OK' % e

    def test_account_post(self):
        """Test account_POST"""
        self._test_0030_account_post()

    def _test_0030_account_post(self):
        r = self.client.account_post()
        self.assertEqual(r.status_code, 202)
        grpName = 'grp' + unicode(self.now)

        """Method set/del_account_meta and set_account_groupcall use
            account_post internally
        """
        u1 = self.client.account
        #  Invalid display name
        u2 = '1nc0r3c7-d15p14y-n4m3'
        self.assertRaises(
            ClientError,
            self.client.set_account_group,
            grpName, [u1, u2])
        self.client.set_account_group(grpName, [u1])
        r = self.client.get_account_group()
        self.assertEqual(r['x-account-group-' + grpName], '%s' % u1)
        self.client.del_account_group(grpName)
        r = self.client.get_account_group()
        self.assertTrue('x-account-group-' + grpName not in r)

        mprefix = 'meta' + unicode(self.now)
        self.client.set_account_meta({
            mprefix + '1': 'v1', mprefix + '2': 'v2'})
        r = self.client.get_account_meta()
        self.assertEqual(r['x-account-meta-' + mprefix + '1'], 'v1')
        self.assertEqual(r['x-account-meta-' + mprefix + '2'], 'v2')

        self.client.del_account_meta(mprefix + '1')
        r = self.client.get_account_meta()
        self.assertTrue('x-account-meta-' + mprefix + '1' not in r)

        self.client.del_account_meta(mprefix + '2')
        r = self.client.get_account_meta()
        self.assertTrue('x-account-meta-' + mprefix + '2' not in r)

        """Missing testing for quota, versioning, because normally
        you don't have permissions to modify those at account level
        """

        #newquota = 1000000
        #self.client.set_account_quota(newquota)
        #r = self.client.get_account_info()
        #print(unicode(r))
        #r = self.client.get_account_quota()
        #self.assertEqual(r['x-account-policy-quota'], newquota)
        #self.client.set_account_versioning('auto')

    def test_container_head(self):
        """Test container_HEAD"""
        self._test_0040_container_head()

    def _test_0040_container_head(self):
        self.client.container = self.c1

        r = self.client.container_head()
        self.assertEqual(r.status_code, 204)

        """Check until"""
        r = self.client.container_head(until=1000000, success=(204, 404))
        self.assertEqual(r.status_code, 404)

        """Check and if(un)modified_since"""
        for format in self.client.DATE_FORMATS:
            now_formated = self.now_unformated.strftime(format)
            r1 = self.client.container_head(
                if_modified_since=now_formated, success=(204, 304, 412))
            sc1 = r1.status_code
            r2 = self.client.container_head(
                if_unmodified_since=now_formated, success=(204, 304, 412))
            sc2 = r2.status_code
            self.assertNotEqual(sc1, sc2)

        """Check container object meta"""
        r = self.client.get_container_object_meta()
        self.assertEqual(r['x-container-object-meta'], 'Incontainer')

    def test_container_get(self):
        """Test container_GET"""
        self._test_0050_container_get()

    def _test_0050_container_get(self):
        self.client.container = self.c1

        r = self.client.container_get()
        self.assertEqual(r.status_code, 200)
        fullLen = len(r.json)

        r = self.client.container_get(prefix='test')
        lalobjects = [obj for obj in r.json if obj['name'].startswith('test')]
        self.assertTrue(len(r.json) > 1)
        self.assertEqual(len(r.json), len(lalobjects))

        r = self.client.container_get(limit=1)
        self.assertEqual(len(r.json), 1)

        r = self.client.container_get(marker='another')
        self.assertTrue(len(r.json) > 1)
        neobjects = [obj for obj in r.json if obj['name'] > 'another']
        self.assertEqual(len(r.json), len(neobjects))

        r = self.client.container_get(prefix='another.test', delimiter='.')
        self.assertTrue(fullLen > len(r.json))

        r = self.client.container_get(path='/')
        self.assertEqual(fullLen, len(r.json))

        r = self.client.container_get(format='xml')
        self.assertEqual(r.text.split()[4], 'name="' + self.c1 + '">')

        r = self.client.container_get(meta=['incontainer'])
        self.assertTrue(len(r.json) > 0)

        r = self.client.container_get(show_only_shared=True)
        self.assertTrue(len(r.json) < fullLen)

        try:
            r = self.client.container_get(until=1000000000)
            datestring = unicode(r.headers['x-account-until-timestamp'])
            self.assertEqual(u'Sun, 09 Sep 2001 01:46:40 GMT', datestring)

        except ClientError:

            pass

        """Check and if un/modified_since"""
        for format in self.client.DATE_FORMATS:
            now_formated = self.now_unformated.strftime(format)
            r1 = self.client.container_get(
                if_modified_since=now_formated, success=(200, 304, 412))
            sc1 = r1.status_code
            r2 = self.client.container_get(
                if_unmodified_since=now_formated, success=(200, 304, 412))
            sc2 = r2.status_code
            self.assertNotEqual(sc1, sc2)

    def test_container_put(self):
        """Test container_PUT"""
        self._test_0050_container_put()

    def _test_0050_container_put(self):
        self.client.container = self.c2

        r = self.client.create_container()
        self.assertTrue(isinstance(r, dict))

        r = self.client.get_container_limit(self.client.container)
        cquota = r.values()[0]
        newquota = 2 * int(cquota)

        r = self.client.create_container(sizelimit=newquota)
        self.assertTrue(isinstance(r, dict))

        r = self.client.get_container_limit(self.client.container)
        xquota = int(r.values()[0])
        self.assertEqual(newquota, xquota)

        r = self.client.create_container(versioning='auto')
        self.assertTrue(isinstance(r, dict))

        r = self.client.get_container_versioning(self.client.container)
        nvers = r.values()[0]
        self.assertEqual('auto', nvers)

        r = self.client.container_put(versioning='none')
        self.assertEqual(r.status_code, 202)

        r = self.client.get_container_versioning(self.client.container)
        nvers = r.values()[0]
        self.assertEqual('none', nvers)

        r = self.client.create_container(metadata={'m1': 'v1', 'm2': 'v2'})
        self.assertTrue(isinstance(r, dict))

        r = self.client.get_container_meta(self.client.container)
        self.assertTrue('x-container-meta-m1' in r)
        self.assertEqual(r['x-container-meta-m1'], 'v1')
        self.assertTrue('x-container-meta-m2' in r)
        self.assertEqual(r['x-container-meta-m2'], 'v2')

        r = self.client.container_put(metadata={'m1': '', 'm2': 'v2a'})
        self.assertEqual(r.status_code, 202)

        r = self.client.get_container_meta(self.client.container)
        self.assertTrue('x-container-meta-m1' not in r)
        self.assertTrue('x-container-meta-m2' in r)
        self.assertEqual(r['x-container-meta-m2'], 'v2a')

        self.client.del_container_meta(self.client.container)

    def test_container_post(self):
        """Test container_POST"""
        self._test_0060_container_post()

    def _test_0060_container_post(self):
        self.client.container = self.c2

        """Simple post"""
        r = self.client.container_post()
        self.assertEqual(r.status_code, 202)

        """post meta"""
        self.client.set_container_meta({'m1': 'v1', 'm2': 'v2'})
        r = self.client.get_container_meta(self.client.container)
        self.assertTrue('x-container-meta-m1' in r)
        self.assertEqual(r['x-container-meta-m1'], 'v1')
        self.assertTrue('x-container-meta-m2' in r)
        self.assertEqual(r['x-container-meta-m2'], 'v2')

        """post/2del meta"""
        r = self.client.del_container_meta('m1')
        r = self.client.set_container_meta({'m2': 'v2a'})
        r = self.client.get_container_meta(self.client.container)
        self.assertTrue('x-container-meta-m1' not in r)
        self.assertTrue('x-container-meta-m2' in r)
        self.assertEqual(r['x-container-meta-m2'], 'v2a')

        """check quota"""
        r = self.client.get_container_limit(self.client.container)
        cquota = r.values()[0]
        newquota = 2 * int(cquota)
        r = self.client.set_container_limit(newquota)
        r = self.client.get_container_limit(self.client.container)
        xquota = int(r.values()[0])
        self.assertEqual(newquota, xquota)
        r = self.client.set_container_limit(cquota)
        r = self.client.get_container_limit(self.client.container)
        xquota = r.values()[0]
        self.assertEqual(cquota, xquota)

        """Check versioning"""
        self.client.set_container_versioning('auto')
        r = self.client.get_container_versioning(self.client.container)
        nvers = r.values()[0]
        self.assertEqual('auto', nvers)
        self.client.set_container_versioning('none')
        r = self.client.get_container_versioning(self.client.container)
        nvers = r.values()[0]
        self.assertEqual('none', nvers)

        """put_block uses content_type and content_length to
        post blocks of data 2 container. All that in upload_object"""
        """Change a file at fs"""
        f = self.create_large_file(1024 * 1024 * 100)
        """Upload it at a directory in container"""
        self.client.create_directory('dir')
        r = self.client.upload_object('/dir/sample.file', f)
        for term in ('content-length', 'content-type', 'x-object-version'):
            self.assertTrue(term in r)
        """Check if file has been uploaded"""
        r = self.client.get_object_info('/dir/sample.file')
        self.assertTrue(int(r['content-length']) > 100000000)

        """What is tranfer_encoding? What should I check about it? """
        #TODO

        """Check update=False"""
        r = self.client.object_post(
            'test',
            update=False,
            metadata={'newmeta': 'newval'})

        r = self.client.get_object_info('test')
        self.assertTrue('x-object-meta-newmeta' in r)
        self.assertFalse('x-object-meta-incontainer' in r)

        r = self.client.del_container_meta('m2')

    def test_container_delete(self):
        """Test container_DELETE"""
        self._test_0070_container_delete()

    def _test_0070_container_delete(self):

        """Fail to delete a non-empty container"""
        self.client.container = self.c2
        r = self.client.container_delete(success=409)
        self.assertEqual(r.status_code, 409)

        """Fail to delete c3 (empty) container"""
        self.client.container = self.c3
        r = self.client.container_delete(until='1000000000')
        self.assertEqual(r.status_code, 204)

        """Delete c3 (empty) container"""
        r = self.client.container_delete()
        self.assertEqual(r.status_code, 204)

        """Purge container(empty a container), check versionlist"""
        self.client.container = self.c1
        r = self.client.object_head('test', success=(200, 404))
        self.assertEqual(r.status_code, 200)
        self.client.del_container(delimiter='/')
        r = self.client.object_head('test', success=(200, 404))
        self.assertEqual(r.status_code, 404)
        r = self.client.get_object_versionlist('test')
        self.assertTrue(len(r) > 0)
        self.assertTrue(len(r[0]) > 1)
        self.client.purge_container()
        self.assertRaises(
            ClientError, self.client.get_object_versionlist, 'test')

    def _test_0080_recreate_deleted_data(self):
        self._init_data()

    def test_object_head(self):
        """Test object_HEAD"""
        self._test_0090_object_head()

    def _test_0090_object_head(self):
        self.client.container = self.c2
        obj = 'test'

        r = self.client.object_head(obj)
        self.assertEqual(r.status_code, 200)
        etag = r.headers['etag']
        real_version = r.headers['x-object-version']

        self.assertRaises(
            ClientError, self.client.object_head, obj, version=-10)
        r = self.client.object_head(obj, version=real_version)
        self.assertEqual(r.headers['x-object-version'], real_version)

        r = self.client.object_head(obj, if_etag_match=etag)
        self.assertEqual(r.status_code, 200)

        r = self.client.object_head(
            obj, if_etag_not_match=etag, success=(200, 412, 304))
        self.assertNotEqual(r.status_code, 200)

        r = self.client.object_head(
            obj, version=real_version, if_etag_match=etag, success=200)
        self.assertEqual(r.status_code, 200)

        """Check and if(un)modified_since"""
        for format in self.client.DATE_FORMATS:
            now_formated = self.now_unformated.strftime(format)
            r1 = self.client.object_head(
                obj, if_modified_since=now_formated, success=(200, 304, 412))
            sc1 = r1.status_code
            r2 = self.client.object_head(
                obj, if_unmodified_since=now_formated, success=(200, 304, 412))
            sc2 = r2.status_code
            self.assertNotEqual(sc1, sc2)

    def test_object_get(self):
        """Test object_GET"""
        self._test_0100_object_get()

    def _test_0100_object_get(self):
        self.client.container = self.c1
        obj = 'test'

        r = self.client.object_get(obj)
        self.assertEqual(r.status_code, 200)

        osize = int(r.headers['content-length'])
        etag = r.headers['etag']

        r = self.client.object_get(obj, hashmap=True)
        for term in ('hashes', 'block_hash', 'block_hash', 'bytes'):
            self.assertTrue(term in r.json)

        r = self.client.object_get(obj, format='xml', hashmap=True)
        self.assertEqual(len(r.text.split('hash>')), 3)

        rangestr = 'bytes=%s-%s' % (osize / 3, osize / 2)
        r = self.client.object_get(
            obj, data_range=rangestr, success=(200, 206))
        partsize = int(r.headers['content-length'])
        self.assertTrue(0 < partsize and partsize <= 1 + osize / 3)

        rangestr = 'bytes=%s-%s' % (osize / 3, osize / 2)
        r = self.client.object_get(
            obj, data_range=rangestr, if_range=True, success=(200, 206))
        partsize = int(r.headers['content-length'])
        self.assertTrue(0 < partsize and partsize <= 1 + osize / 3)

        r = self.client.object_get(obj, if_etag_match=etag)
        self.assertEqual(r.status_code, 200)

        r = self.client.object_get(obj, if_etag_not_match=etag + 'LALALA')
        self.assertEqual(r.status_code, 200)

        """Check and if(un)modified_since"""
        for format in self.client.DATE_FORMATS:
            now_formated = self.now_unformated.strftime(format)
            r1 = self.client.object_get(
                obj, if_modified_since=now_formated, success=(200, 304, 412))
            sc1 = r1.status_code
            r2 = self.client.object_get(
                obj, if_unmodified_since=now_formated, success=(200, 304, 412))
            sc2 = r2.status_code
            self.assertNotEqual(sc1, sc2)

        """Upload an object to download"""
        container_info_cache = dict()
        trg_fname = 'remotefile_%s' % self.now
        f_size = 59247824
        src_f = self.create_large_file(f_size)
        print('\tUploading...')
        r = self.client.upload_object(
            trg_fname, src_f, container_info_cache=container_info_cache)
        print('\tDownloading...')
        self.files.append(NamedTemporaryFile())
        dnl_f = self.files[-1]
        self.client.download_object(trg_fname, dnl_f)

        print('\tCheck if files match...')
        for pos in (0, f_size / 2, f_size - 128):
            src_f.seek(pos)
            dnl_f.seek(pos)
            self.assertEqual(src_f.read(64), dnl_f.read(64))

        print('\tDownload KiBs to string and check again...')
        for pos in (0, f_size / 2, f_size - 256):
            src_f.seek(pos)
            tmp_s = self.client.download_to_string(
                trg_fname, range_str='%s-%s' % (pos, (pos + 128)))
            self.assertEqual(tmp_s, src_f.read(len(tmp_s)))
        print('\tUploading KiBs as strings...')
        trg_fname = 'fromString_%s' % self.now
        src_size = 2 * 1024
        src_f.seek(0)
        src_str = src_f.read(src_size)
        self.client.upload_from_string(trg_fname, src_str)
        print('\tDownload as string and check...')
        tmp_s = self.client.download_to_string(trg_fname)
        self.assertEqual(tmp_s, src_str)

        """Upload a boring file"""
        trg_fname = 'boringfile_%s' % self.now
        src_f = self.create_boring_file(42)
        print('\tUploading boring file...')
        self.client.upload_object(
            trg_fname, src_f, container_info_cache=container_info_cache)
        print('\tDownloading boring file...')
        self.files.append(NamedTemporaryFile())
        dnl_f = self.files[-1]
        self.client.download_object(trg_fname, dnl_f)

        print('\tCheck if files match...')
        for i in range(42):
            self.assertEqual(sample_block(src_f, i), sample_block(dnl_f, i))

    def test_object_put(self):
        """Test object_PUT"""
        self._test_0150_object_put()

    def _test_0150_object_put(self):
        self.client.container = self.c2
        obj = 'another.test'

        self.client.create_object(obj + '.FAKE')
        r = self.client.get_object_info(obj + '.FAKE')
        self.assertEqual(r['content-type'], 'application/octet-stream')

        """create the object"""
        r = self.client.object_put(
            obj,
            data='a',
            content_type='application/octer-stream',
            permissions=dict(
                read=['accX:groupA', 'u1', 'u2'],
                write=['u2', 'u3']),
            metadata=dict(key1='val1', key2='val2'),
            content_encoding='UTF-8',
            content_disposition='attachment; filename="fname.ext"')
        self.assertEqual(r.status_code, 201)
        etag = r.headers['etag']

        """Check content-disposition"""
        r = self.client.get_object_info(obj)
        self.assertTrue('content-disposition' in r)

        """Check permissions"""
        r = self.client.get_object_sharing(obj)
        self.assertTrue('accx:groupa' in r['read'])
        self.assertTrue('u1' in r['read'])
        self.assertTrue('u2' in r['write'])
        self.assertTrue('u3' in r['write'])

        """Check metadata"""
        r = self.client.get_object_meta(obj)
        self.assertEqual(r['x-object-meta-key1'], 'val1')
        self.assertEqual(r['x-object-meta-key2'], 'val2')

        """Check public and if_etag_match"""
        r = self.client.object_put(
            obj,
            if_etag_match=etag,
            data='b',
            content_type='application/octet-stream',
            public=True)

        r = self.client.object_get(obj)
        self.assertTrue('x-object-public' in r.headers)
        vers2 = int(r.headers['x-object-version'])
        etag = r.headers['etag']
        self.assertEqual(r.text, 'b')

        """Check if_etag_not_match"""
        r = self.client.object_put(
            obj,
            if_etag_not_match=etag,
            data='c',
            content_type='application/octet-stream',
            success=(201, 412))
        self.assertEqual(r.status_code, 412)

        """Check content_type and content_length"""
        tmpdir = 'dir' + unicode(self.now)
        r = self.client.object_put(
            tmpdir, content_type='application/directory', content_length=0)

        r = self.client.get_object_info(tmpdir)
        self.assertEqual(r['content-type'], 'application/directory')

        """Check copy_from, content_encoding"""
        r = self.client.object_put(
            '%s/%s' % (tmpdir, obj),
            format=None,
            copy_from='/%s/%s' % (self.client.container, obj),
            content_encoding='application/octet-stream',
            source_account=self.client.account,
            content_length=0,
            success=201)
        self.assertEqual(r.status_code, 201)

        """Test copy_object for cross-conctainer copy"""
        self.client.copy_object(
            src_container=self.c2,
            src_object='%s/%s' % (tmpdir, obj),
            dst_container=self.c1,
            dst_object=obj)
        self.client.container = self.c1
        r1 = self.client.get_object_info(obj)
        self.client.container = self.c2
        r2 = self.client.get_object_info('%s/%s' % (tmpdir, obj))
        self.assertEqual(r1['x-object-hash'], r2['x-object-hash'])

        """Check cross-container copy_from, content_encoding"""
        self.client.container = self.c1
        fromstr = '/%s/%s/%s' % (self.c2, tmpdir, obj)
        r = self.client.object_put(
            obj,
            format=None,
            copy_from=fromstr,
            content_encoding='application/octet-stream',
            source_account=self.client.account,
            content_length=0,
            success=201)

        self.assertEqual(r.status_code, 201)
        r = self.client.get_object_info(obj)
        self.assertEqual(r['etag'], etag)

        """Check source_account"""
        self.client.container = self.c2
        fromstr = '/%s/%s' % (self.c1, obj)
        r = self.client.object_put(
            '%sv2' % obj,
            format=None,
            move_from=fromstr,
            content_encoding='application/octet-stream',
            source_account='nonExistendAddress@NeverLand.com',
            content_length=0,
            success=(201, 403))
        self.assertEqual(r.status_code, 403)

        """Check cross-container move_from"""
        self.client.container = self.c1
        r1 = self.client.get_object_info(obj)
        self.client.container = self.c2
        self.client.move_object(
            src_container=self.c1,
            src_object=obj,
            dst_container=self.c2,
            dst_object=obj + 'v0')
        r0 = self.client.get_object_info(obj + 'v0')
        self.assertEqual(r1['x-object-hash'], r0['x-object-hash'])

        """Check move_from"""
        r = self.client.object_put(
            '%sv1' % obj,
            format=None,
            move_from='/%s/%s' % (self.c2, obj),
            source_version=vers2,
            content_encoding='application/octet-stream',
            content_length=0, success=201)

        """Check manifest"""
        mobj = 'manifest.test'
        txt = ''
        for i in range(10):
            txt += '%s' % i
            r = self.client.object_put(
                '%s/%s' % (mobj, i),
                data='%s' % i,
                content_length=1,
                success=201,
                content_type='application/octet-stream',
                content_encoding='application/octet-stream')

        r = self.client.object_put(
            mobj,
            content_length=0,
            content_type='application/octet-stream',
            manifest='%s/%s' % (self.client.container, mobj))

        r = self.client.object_get(mobj)
        self.assertEqual(r.text, txt)

        """Upload a local file with one request"""
        newf = self.create_large_file(1024 * 10)
        self.client.upload_object('sample.file', newf)
        """Check if file has been uploaded"""
        r = self.client.get_object_info('sample.file')
        self.assertEqual(int(r['content-length']), 10240)

        """Some problems with transfer-encoding?"""

    def test_object_copy(self):
        """Test object_COPY"""
        self._test_0110_object_copy()

    def _test_0110_object_copy(self):
        #  TODO: check with source_account option
        self.client.container = self.c2
        obj = 'test2'

        data = '{"key1":"val1", "key2":"val2"}'
        r = self.client.object_put(
            '%sorig' % obj,
            content_type='application/octet-stream',
            data=data,
            metadata=dict(mkey1='mval1', mkey2='mval2'),
            permissions=dict(
                read=['accX:groupA', 'u1', 'u2'],
                write=['u2', 'u3']),
            content_disposition='attachment; filename="fname.ext"')

        r = self.client.object_copy(
            '%sorig' % obj,
            destination='/%s/%s' % (self.client.container, obj),
            ignore_content_type=False, content_type='application/json',
            metadata={'mkey2': 'mval2a', 'mkey3': 'mval3'},
            permissions={'write': ['u5', 'accX:groupB']})
        self.assertEqual(r.status_code, 201)

        """Check content-disposition"""
        r = self.client.get_object_info(obj)
        self.assertTrue('content-disposition' in r)

        """Check Metadata"""
        r = self.client.get_object_meta(obj)
        self.assertEqual(r['x-object-meta-mkey1'], 'mval1')
        self.assertEqual(r['x-object-meta-mkey2'], 'mval2a')
        self.assertEqual(r['x-object-meta-mkey3'], 'mval3')

        """Check permissions"""
        r = self.client.get_object_sharing(obj)
        self.assertFalse('read' in r or 'u2' in r['write'])
        self.assertTrue('accx:groupb' in r['write'])

        """Check destination account"""
        r = self.client.object_copy(
            obj,
            destination='/%s/%s' % (self.c1, obj),
            content_encoding='utf8',
            content_type='application/json',
            destination_account='nonExistendAddress@NeverLand.com',
            success=(201, 404))
        self.assertEqual(r.status_code, 404)

        """Check destination being another container
        and also content_type and content encoding"""
        r = self.client.object_copy(
            obj,
            destination='/%s/%s' % (self.c1, obj),
            content_encoding='utf8',
            content_type='application/json')
        self.assertEqual(r.status_code, 201)
        self.assertEqual(
            r.headers['content-type'],
            'application/json; charset=UTF-8')

        """Check ignore_content_type and content_type"""
        r = self.client.object_get(obj)
        etag = r.headers['etag']
        ctype = r.headers['content-type']
        self.assertEqual(ctype, 'application/json')

        r = self.client.object_copy(
            '%sorig' % obj,
            destination='/%s/%s0' % (self.client.container, obj),
            ignore_content_type=True,
            content_type='application/json')
        self.assertEqual(r.status_code, 201)
        self.assertNotEqual(r.headers['content-type'], 'application/json')

        """Check if_etag_(not_)match"""
        r = self.client.object_copy(
            obj,
            destination='/%s/%s1' % (self.client.container, obj),
            if_etag_match=etag)
        self.assertEqual(r.status_code, 201)

        r = self.client.object_copy(
            obj,
            destination='/%s/%s2' % (self.client.container, obj),
            if_etag_not_match='lalala')
        self.assertEqual(r.status_code, 201)
        vers2 = r.headers['x-object-version']

        """Check source_version, public and format """
        r = self.client.object_copy(
            '%s2' % obj,
            destination='/%s/%s3' % (self.client.container, obj),
            source_version=vers2,
            format='xml',
            public=True)
        self.assertEqual(r.status_code, 201)
        self.assertTrue(r.headers['content-type'].index('xml') > 0)

        r = self.client.get_object_info(obj + '3')
        self.assertTrue('x-object-public' in r)

    def test_object_move(self):
        """Test object_MOVE"""
        self._test_0120_object_move()

    def _test_0120_object_move(self):
        self.client.container = self.c2
        obj = 'test2'

        data = '{"key1": "val1", "key2": "val2"}'
        r = self.client.object_put(
            '%sorig' % obj,
            content_type='application/octet-stream',
            data=data,
            metadata=dict(mkey1='mval1', mkey2='mval2'),
            permissions=dict(
                read=['accX:groupA', 'u1', 'u2'],
                write=['u2', 'u3']))

        r = self.client.object_move(
            '%sorig' % obj,
            destination='/%s/%s' % (self.client.container, obj),
            ignore_content_type=False,
            content_type='application/json',
            metadata=dict(mkey2='mval2a', mkey3='mval3'),
            permissions=dict(write=['u5', 'accX:groupB']))
        self.assertEqual(r.status_code, 201)

        """Check Metadata"""
        r = self.client.get_object_meta(obj)
        self.assertEqual(r['x-object-meta-mkey1'], 'mval1')
        self.assertEqual(r['x-object-meta-mkey2'], 'mval2a')
        self.assertEqual(r['x-object-meta-mkey3'], 'mval3')

        """Check permissions"""
        r = self.client.get_object_sharing(obj)
        self.assertFalse('read' in r)
        self.assertTrue('u5' in r['write'])
        self.assertTrue('accx:groupb' in r['write'])

        """Check destination account"""
        r = self.client.object_move(
            obj,
            destination='/%s/%s' % (self.c1, obj),
            content_encoding='utf8',
            content_type='application/json',
            destination_account='nonExistendAddress@NeverLand.com',
            success=(201, 404))
        self.assertEqual(r.status_code, 404)

        """Check destination being another container and also
        content_type, content_disposition and content encoding"""
        r = self.client.object_move(
            obj,
            destination='/%s/%s' % (self.c1, obj),
            content_encoding='utf8',
            content_type='application/json',
            content_disposition='attachment; filename="fname.ext"')
        self.assertEqual(r.status_code, 201)
        self.assertEqual(
            r.headers['content-type'],
            'application/json; charset=UTF-8')
        self.client.container = self.c1
        r = self.client.get_object_info(obj)
        self.assertTrue('content-disposition' in r)
        self.assertTrue('fname.ext' in r['content-disposition'])
        etag = r['etag']
        ctype = r['content-type']
        self.assertEqual(ctype, 'application/json')

        """Check ignore_content_type and content_type"""
        r = self.client.object_move(
            obj,
            destination='/%s/%s' % (self.c2, obj),
            ignore_content_type=True,
            content_type='application/json')
        self.assertEqual(r.status_code, 201)
        self.assertNotEqual(r.headers['content-type'], 'application/json')

        """Check if_etag_(not_)match"""
        self.client.container = self.c2
        r = self.client.object_move(
            obj,
            destination='/%s/%s0' % (self.client.container, obj),
            if_etag_match=etag)
        self.assertEqual(r.status_code, 201)

        r = self.client.object_move(
            '%s0' % obj,
            destination='/%s/%s1' % (self.client.container, obj),
            if_etag_not_match='lalala')
        self.assertEqual(r.status_code, 201)

        """Check public and format """
        r = self.client.object_move(
            '%s1' % obj,
            destination='/%s/%s2' % (self.client.container, obj),
            format='xml',
            public=True)
        self.assertEqual(r.status_code, 201)
        self.assertTrue(r.headers['content-type'].index('xml') > 0)

        r = self.client.get_object_info(obj + '2')
        self.assertTrue('x-object-public' in r)

    def test_object_post(self):
        """Test object_POST"""
        self._test_0130_object_post()

    def _test_0130_object_post(self):
        self.client.container = self.c2
        obj = 'test2'

        """create a filesystem file"""
        self.files.append(NamedTemporaryFile())
        newf = self.files[-1]
        newf.writelines([
            'ello!\n',
            'This is a test line\n',
            'inside a test file\n'])

        """create a file on container"""
        r = self.client.object_put(
            obj,
            content_type='application/octet-stream',
            data='H',
            metadata=dict(mkey1='mval1', mkey2='mval2'),
            permissions=dict(
                read=['accX:groupA', 'u1', 'u2'],
                write=['u2', 'u3']))

        """Append livetest update, content_[range|type|length]"""
        newf.seek(0)
        self.client.append_object(obj, newf)
        r = self.client.object_get(obj)
        self.assertTrue(r.text.startswith('Hello!'))

        """Overwrite livetest update,
            content_type, content_length, content_range
        """
        newf.seek(0)
        r = self.client.overwrite_object(obj, 0, 10, newf)
        r = self.client.object_get(obj)
        self.assertTrue(r.text.startswith('ello!'))

        """Truncate livetest update,
            content_range, content_type, object_bytes and source_object"""
        r = self.client.truncate_object(obj, 5)
        r = self.client.object_get(obj)
        self.assertEqual(r.text, 'ello!')

        """Check metadata"""
        self.client.set_object_meta(obj, {'mkey2': 'mval2a', 'mkey3': 'mval3'})
        r = self.client.get_object_meta(obj)
        self.assertEqual(r['x-object-meta-mkey1'], 'mval1')
        self.assertEqual(r['x-object-meta-mkey2'], 'mval2a')
        self.assertEqual(r['x-object-meta-mkey3'], 'mval3')
        self.client.del_object_meta(obj, 'mkey1')
        r = self.client.get_object_meta(obj)
        self.assertFalse('x-object-meta-mkey1' in r)

        """Check permissions"""
        self.client.set_object_sharing(
            obj, read_permission=['u4', 'u5'], write_permission=['u4'])
        r = self.client.get_object_sharing(obj)
        self.assertTrue('read' in r)
        self.assertTrue('u5' in r['read'])
        self.assertTrue('write' in r)
        self.assertTrue('u4' in r['write'])
        self.client.del_object_sharing(obj)
        r = self.client.get_object_sharing(obj)
        self.assertTrue(len(r) == 0)

        """Check publish"""
        self.client.publish_object(obj)
        r = self.client.get_object_info(obj)
        self.assertTrue('x-object-public' in r)
        self.client.unpublish_object(obj)
        r = self.client.get_object_info(obj)
        self.assertFalse('x-object-public' in r)

        """Check if_etag_(not)match"""
        etag = r['etag']
        r = self.client.object_post(
            obj,
            update=True,
            public=True,
            if_etag_not_match=etag,
            success=(412, 202, 204))
        #self.assertEqual(r.status_code, 412)

        r = self.client.object_post(
            obj,
            update=True,
            public=True,
            if_etag_match=etag,
            content_encoding='application/json')

        r = self.client.get_object_info(obj)
        helloVersion = r['x-object-version']
        self.assertTrue('x-object-public' in r)
        self.assertEqual(r['content-encoding'], 'application/json')

        """Check source_version and source_account and content_disposition"""
        r = self.client.object_post(
            obj,
            update=True,
            content_type='application/octet-srteam',
            content_length=5,
            content_range='bytes 1-5/*',
            source_object='/%s/%s' % (self.c2, obj),
            source_account='thisAccountWillNeverExist@adminland.com',
            source_version=helloVersion,
            data='12345',
            success=(403, 202, 204))
        self.assertEqual(r.status_code, 403)

        r = self.client.object_post(
            obj,
            update=True,
            content_type='application/octet-srteam',
            content_length=5,
            content_range='bytes 1-5/*',
            source_object='/%s/%s' % (self.c2, obj),
            source_account=self.client.account,
            source_version=helloVersion,
            data='12345',
            content_disposition='attachment; filename="fname.ext"')

        r = self.client.object_get(obj)
        self.assertEqual(r.text, 'eello!')
        self.assertTrue('content-disposition' in r.headers)
        self.assertTrue('fname.ext' in r.headers['content-disposition'])

        """Check manifest"""
        mobj = 'manifest.test'
        txt = ''
        for i in range(10):
            txt += '%s' % i
            r = self.client.object_put(
                '%s/%s' % (mobj, i),
                data='%s' % i,
                content_length=1,
                success=201,
                content_encoding='application/octet-stream',
                content_type='application/octet-stream')

        self.client.create_object_by_manifestation(
            mobj, content_type='application/octet-stream')

        r = self.client.object_post(
            mobj, manifest='%s/%s' % (self.client.container, mobj))

        r = self.client.object_get(mobj)
        self.assertEqual(r.text, txt)

        """We need to check transfer_encoding """

    def test_object_delete(self):
        """Test object_DELETE"""
        self._test_0140_object_delete()

    def _test_0140_object_delete(self):
        self.client.container = self.c2
        obj = 'test2'
        """create a file on container"""
        r = self.client.object_put(
            obj,
            content_type='application/octet-stream',
            data='H',
            metadata=dict(mkey1='mval1', mkey2='mval2'),
            permissions=dict(
                read=['accX:groupA', 'u1', 'u2'],
                write=['u2', 'u3']))

        """Check with false until"""
        r = self.client.object_delete(obj, until=1000000)

        r = self.client.object_get(obj, success=(200, 404))
        self.assertEqual(r.status_code, 200)

        """Check normal case"""
        r = self.client.object_delete(obj)
        self.assertEqual(r.status_code, 204)

        r = self.client.object_get(obj, success=(200, 404))
        self.assertEqual(r.status_code, 404)

    def create_large_file(self, size):
        """Create a large file at fs"""
        print
        self.files.append(NamedTemporaryFile())
        f = self.files[-1]
        Ki = size / 8
        bytelist = [b * Ki for b in range(size / Ki)]

        def append2file(step):
            f.seek(step)
            f.write(urandom(Ki))
            f.flush()
        self.do_with_progress_bar(
            append2file,
            ' create rand file %s (%sB): ' % (f.name, size),
            bytelist)
        f.seek(0)
        return f

    def create_boring_file(self, num_of_blocks):
        """Create a file with some blocks being the same"""
        self.files.append(NamedTemporaryFile())
        tmpFile = self.files[-1]
        block_size = 4 * 1024 * 1024
        print('\n\tCreate boring file of %s blocks' % num_of_blocks)
        chars = chargen()
        while num_of_blocks:
            fslice = 3 if num_of_blocks > 3 else num_of_blocks
            tmpFile.write(fslice * block_size * chars.next())
            num_of_blocks -= fslice
        print('\t\tDone')
        tmpFile.seek(0)
        return tmpFile
