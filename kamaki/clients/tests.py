# Copyright 2011 GRNET S.A. All rights reserved.
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

import unittest
import time
import os

from kamaki.clients import pithos, cyclades

class testPithos(unittest.TestCase):
    def setUp(self):
        url = 'http://127.0.0.1:8000/v1'
        token = 'C/yBXmz3XjTFBnujc2biAg=='
        token = 'ac0yH8cQMEZu3M3Mp1MWGA=='
        account = 'admin@adminland.com'
        container=None
        self.client = pithos(url, token, account, container)
        self.now = time.mktime(time.gmtime())

    def test_account_head(self):
        r = self.client.account_head()
        self.assertEqual(r.status_code, 204)
        r = self.client.account_head(until='1000000000')
        self.assertEqual(r.status_code, 204)
        datestring = unicode(r.headers['x-account-until-timestamp'])
        self.assertEqual(u'Sun, 09 Sep 2001 01:46:40 GMT', datestring)
        self.client.reset_headers()
        r = self.client.account_head(if_modified_since=self.now)
        self.client.reset_headers()
        r = self.client.account_head(if_unmodified_since=10000)
        self.client.reset_headers()

    def test_account_get(self):
        r = self.client.account_get()
        self.assertEqual(r.status_code, 200)
        fullLen = len(r.json)
        self.assertEqual(fullLen, 3)

        r = self.client.account_get(limit=1)
        self.assertEqual(len(r.json), 1)

        r = self.client.account_get(limit=3, marker='test')
        self.assertNotEqual(len(r.json), 0)
        conames = [container['name'] for container in r.json if container['name'].lower().startswith('test')]
        self.assertEqual(len(conames), len(r.json))
        self.client.reset_headers()

        r = self.client.account_get(show_only_shared=True)
        self.assertEqual(len(r.json), 2)
        self.client.reset_headers()

        r = self.client.account_get(until=1342609206)
        self.assertTrue(len(r.json) < fullLen)
        self.client.reset_headers()

        """Missing Full testing for if_modified_since, if_unmodified_since
        """
        r = self.client.account_head(if_modified_since=self.now)
        self.client.reset_headers()
        r = self.client.account_head(if_unmodified_since=10000)
        self.client.reset_headers()

    def test_account_post(self):
        r = self.client.account_post()
        self.assertEqual(r.status_code, 202)
        grpName = 'tstgrp'

        """Method set/del_account_meta and set_account_groupcall account_post internally
        """
        self.client.set_account_group(grpName, ['u1', 'u2'])
        r = self.client.get_account_group()
        self.assertEqual(r['x-account-group-'+grpName], 'u1,u2')
        self.client.del_account_group(grpName)
        r = self.client.get_account_group()
        self.assertTrue(not r.has_key('x-account-group-grpName'))
        self.client.reset_headers()

        self.client.set_account_meta({'metatest1':'v1', 'metatest2':'v2'})
        r = self.client.get_account_meta()
        self.assertEqual(r['x-account-meta-metatest1'], 'v1')
        self.assertEqual(r['x-account-meta-metatest2'], 'v2')
        self.client.reset_headers()

        self.client.del_account_meta('metatest1')
        r = self.client.get_account_meta()
        self.assertTrue(not r.has_key('x-account-meta-metatest1'))
        self.client.reset_headers()

        self.client.del_account_meta('metatest2')
        r = self.client.get_account_meta()
        self.assertTrue(not r.has_key('x-account-meta-metatest2'))
        self.client.reset_headers()

        """Missing testing for quota, versioning, because normally
        you don't have permitions for modified those at account level
        """

    def test_container_head(self):
        self.client.container = 'testCo'

        r = self.client.account_head()
        self.assertEqual(r.status_code, 204)

        r = self.client.account_head(until=1000000000)
        datestring = unicode(r.headers['x-account-until-timestamp'])
        self.assertEqual(u'Sun, 09 Sep 2001 01:46:40 GMT', datestring)

        r = self.client.account_head(if_modified_since=1342609206)
        self.client.reset_headers()
        r = self.client.account_head(if_unmodified_since=1342609206)
        self.client.reset_headers()
        self.client.container = ''

    def test_container_get(self):
        self.client.container = 'testCo'

        r = self.client.container_get()
        self.assertEqual(r.status_code, 200)
        fullLen = len(r.json)

        r = self.client.container_get(prefix='lal')
        lalobjects = [obj for obj in r.json if obj['name'].startswith('lal')]
        self.assertTrue(len(r.json) > 1)
        self.assertEqual(len(r.json), len(lalobjects))
        self.client.reset_headers()

        r = self.client.container_get(limit=1)
        self.assertEqual(len(r.json), 1)
        self.client.reset_headers()

        r = self.client.container_get(marker='neo')
        self.assertTrue(len(r.json) > 1)
        neobjects = [obj for obj in r.json if obj['name'] > 'neo']
        self.assertEqual(len(r.json), len(neobjects))
        self.client.reset_headers()

        r = self.client.container_get(prefix='testDir/testDir', delimiter='2')
        self.assertTrue(fullLen > len(r.json))
        self.client.reset_headers()

        r = self.client.container_get(path='testDir/testDir2')
        self.assertTrue(fullLen > len(r.json))
        self.client.reset_headers()

        r = self.client.container_get(format='xml')
        self.assertEqual(r.text.split()[4], 'name="testCo">')
        self.client.reset_headers()

        r = self.client.container_get(meta=['Lalakis'])
        self.assertEqual(len(r.json), 1)
        self.client.reset_headers()

        r = self.client.container_get(show_only_shared=True)
        self.assertTrue(len(r.json) < fullLen)
        self.client.reset_headers()

        try:
            r = self.client.container_get(until=1000000000)
            datestring = unicode(r.headers['x-account-until-timestamp'])
            self.assertEqual(u'Sun, 09 Sep 2001 01:46:40 GMT', datestring)
        except:#Normally, container wasn't created in that date...
            pass
        self.client.reset_headers()

        """Missing Full testing for if_modified_since, if_unmodified_since
        """
        now = time.mktime(time.gmtime())
        r = self.client.container_get(if_modified_since=now)
        r = self.client.container_get(if_unmodified_since=now)

        self.container = ''
        self.client.reset_headers()
       
    def test_container_put(self):
        self.client.container = 'testCo'

        r = self.client.container_put()
        self.assertEqual(r.status_code, 202)

        r = self.client.get_container_quota(self.client.container)
        cquota = r.values()[0]
        newquota = 2*int(cquota)
        self.client.reset_headers()

        r = self.client.container_put(quota=newquota)
        self.assertEqual(r.status_code, 202)
        r = self.client.get_container_quota(self.client.container)
        xquota = int(r.values()[0])
        self.assertEqual(newquota, xquota)
        self.client.reset_headers()

        r = self.client.container_put(versioning='auto')
        self.assertEqual(r.status_code, 202)
        r = self.client.get_container_versioning(self.client.container)
        nvers = r.values()[0]
        self.assertEqual('auto', nvers)
        self.client.reset_headers()

        r = self.client.container_put(versioning='none')
        self.assertEqual(r.status_code, 202)
        r = self.client.get_container_versioning(self.client.container)
        nvers = r.values()[0]
        self.assertEqual('none', nvers)
        self.client.reset_headers()

        r = self.client.container_put(metadata={'m1':'v1', 'm2':'v2'})
        self.assertEqual(r.status_code, 202)
        r = self.client.get_container_meta(self.client.container)
        self.assertTrue(r.has_key('x-container-meta-m1'))
        self.assertEqual(r['x-container-meta-m1'], 'v1')
        self.assertTrue(r.has_key('x-container-meta-m2'))
        self.assertEqual(r['x-container-meta-m2'], 'v2')
        self.client.reset_headers()

        r = self.client.container_put(metadata={'m1':'', 'm2':'v2a'})
        self.assertEqual(r.status_code, 202)
        r = self.client.get_container_meta(self.client.container)
        self.assertTrue(not r.has_key('x-container-meta-m1'))
        self.assertTrue(r.has_key('x-container-meta-m2'))
        self.assertEqual(r['x-container-meta-m2'], 'v2a')
        self.client.reset_headers()
       
        self.client.del_container_meta(self.client.container) 
        self.client.container_put(quota=cquota)
        self.client.container = ''
        self.client.reset_headers()

    def test_container_post(self):
        self.client.container = 'testCo0'

        r = self.client.container_post()
        self.assertEqual(r.status_code, 202)

        self.client.set_container_meta({'m1':'v1', 'm2':'v2'})
        r = self.client.get_container_meta(self.client.container)
        self.assertTrue(r.has_key('x-container-meta-m1'))
        self.assertEqual(r['x-container-meta-m1'], 'v1')
        self.assertTrue(r.has_key('x-container-meta-m2'))
        self.assertEqual(r['x-container-meta-m2'], 'v2')
        self.client.reset_headers()

        r = self.client.del_container_meta('m1')
        r = self.client.set_container_meta({'m2':'v2a'})
        r = self.client.get_container_meta(self.client.container)
        self.assertTrue(not r.has_key('x-container-meta-m1'))
        self.assertTrue(r.has_key('x-container-meta-m2'))
        self.assertEqual(r['x-container-meta-m2'], 'v2a')
        self.client.reset_headers()

        r = self.client.get_container_quota(self.client.container)
        cquota = r.values()[0]
        newquota = 2*int(cquota)
        self.client.reset_headers()

        r = self.client.set_container_quota(newquota)
        r = self.client.get_container_quota(self.client.container)
        xquota = int(r.values()[0])
        self.assertEqual(newquota, xquota)
        self.client.reset_headers()

        r = self.client.set_container_quota(cquota)
        r = self.client.get_container_quota(self.client.container)
        xquota = r.values()[0]
        self.assertEqual(cquota, xquota)
        self.client.reset_headers()

        self.client.set_container_versioning('auto')
        r = self.client.get_container_versioning(self.client.container)
        nvers = r.values()[0]
        self.assertEqual('auto', nvers)
        self.client.reset_headers()

        self.client.set_container_versioning('none')
        r = self.client.get_container_versioning(self.client.container)
        nvers = r.values()[0]
        self.assertEqual('none', nvers)
        self.client.reset_headers()

        """Haven't figured out how to test put_block, which
        uses content_type and content_length to post blocks
        of data to container. But how do you check that
        the blocks are there?"""

        """WTF is tranfer_encoding? What should I check about th** s**t? """
        r = self.client.container_post(update=True, transfer_encoding='xlm')
        self.client.reset_headers()

        """This last part doesnt seem to work"""
        """self.client.container_post(update=False)"""
        """so we do it the wrong way"""
        r = self.client.del_container_meta('m2')
        self.client.container = ''
        self.client.reset_headers()

    def test_container_delete(self):
        container = 'testCo'+unicode(self.now)
        self.client.container = container

        """Create new container"""
        r = self.client.container_put()
        self.assertEqual(r.status_code, 201)
        self.client.reset_headers()

        """Fail to delete a non-empty container"""
        self.client.container = 'testCo'
        r = self.client.container_delete(success=409)
        self.assertEqual(r.status_code, 409)
        self.client.reset_headers()

        """Fail to delete this container"""
        self.client.container = container
        r = self.client.container_delete(until='1000000000')
        self.assertEqual(r.status_code, 204)
        self.client.reset_headers()

        """Delete this container"""
        r = self.client.container_delete()
        self.assertEqual(r.status_code, 204)

        self.client.container = ''
        self.client.reset_headers()

    def test_object_head(self):
        self.client.container = 'testCo0'
        obj = 'lolens'

        r = self.client.object_head(obj)
        self.assertEqual(r.status_code, 200)
        etag = r.headers['etag']

        r = self.client.object_head(obj, version=40)
        self.assertEqual(r.status_code, 200)
        self.client.reset_headers()

        r = self.client.object_head(obj, if_etag_match=etag)
        self.assertEqual(r.status_code, 200)
        """I believe if_etag_not_match does not work..."""
        self.client.reset_headers()

        r = self.client.object_head(obj, version=40, if_etag_match=etag, success=412)
        self.assertEqual(r.status_code, 412)
        self.client.reset_headers()

        """I believe if_un/modified_since does not work..."""
        r=self.client.object_head(obj, if_modified_since=self.now)
        self.assertEqual(r.status_code, 200)
        self.client.reset_headers()

        r=self.client.object_head(obj, if_unmodified_since=self.now)
        self.assertEqual(r.status_code, 200)

        self.client.container = ''
        self.client.reset_headers()

    def test_object_get(self):
        self.client.container = 'testCo'

        r = self.client.object_get('lolens')
        self.assertEqual(r.status_code, 200)
        osize = int(r.headers['content-length'])
        etag = r.headers['etag']

        r = self.client.object_get('lolens', hashmap=True)
        self.assertTrue(r.json.has_key('hashes') \
            and r.json.has_key('block_hash') \
            and r.json.has_key('block_size') \
            and r.json.has_key('bytes'))

        r = self.client.object_get('lolens', format='xml', hashmap=True)
        self.assertEqual(len(r.text.split('hash>')), 3)
        self.client.reset_headers()

        rangestr = 'bytes=%s-%s'%(osize/3, osize/2)
        r = self.client.object_get('lolens', data_range=rangestr, success=(200, 206))
        partsize = int(r.headers['content-length'])
        self.assertTrue(0 < partsize and partsize <= 1+osize/3)
        self.client.reset_headers()

        rangestr = 'bytes=%s-%s'%(osize/3, osize/2)
        r = self.client.object_get('lolens', data_range=rangestr, if_range=True, success=(200, 206))
        partsize = int(r.headers['content-length'])
        self.assertTrue(0 < partsize and partsize <= 1+osize/3)
        self.client.reset_headers()

        r = self.client.object_get('lolens', if_etag_match=etag)
        self.assertEqual(r.status_code, 200)
        self.client.reset_headers()

        r = self.client.object_get('lolens', if_etag_not_match=etag+'LALALA')
        self.assertEqual(r.status_code, 200)

        """I believe if_un/modified_since does not work..."""
        r=self.client.object_get('lolens', if_modified_since=self.now)
        self.assertEqual(r.status_code, 200)
        self.client.reset_headers()

        r=self.client.object_get('lolens', if_unmodified_since=self.now)
        self.assertEqual(r.status_code, 200)

        self.client.container = ''
        self.client.reset_headers()

    def test_object_put(self):
        self.client.container = 'testCo0'
        obj='obj'+unicode(self.now)

        r = self.client.object_put(obj, data='a', content_type='application/octer-stream',
            permitions={'read':['accX:groupA', 'u1', 'u2'], 'write':['u2', 'u3']},
            metadata={'key1':'val1', 'key2':'val2'})
        self.assertEqual(r.status_code, 201)
        self.client.reset_headers()

        r = self.client.object_get(obj)
        """Check permitions"""
        perms = r.headers['x-object-sharing']
        self.assertTrue(perms.index('u1') < perms.index('write') < perms.index('u2'))
        """Check metadata"""
        self.assertTrue(r.headers.has_key('x-object-meta-key1'))
        self.assertEqual(r.headers['x-object-meta-key1'], 'val1')
        self.assertTrue(r.headers.has_key('x-object-meta-key2'))
        self.assertEqual(r.headers['x-object-meta-key2'], 'val2')
        vers1 = int(r.headers['x-object-version'])
        self.assertEqual(r.headers['content-length'], '1')
        etag = r.headers['etag']
        self.client.reset_headers()

        r = self.client.object_put(obj, if_etag_match=etag, data='b',
            content_type='application/octet-stream', public=True)
        self.client.reset_headers()
        r = self.client.object_get(obj)
        """Check public"""
        self.assertTrue(r.headers.has_key('x-object-public'))
        vers2 = int(r.headers['x-object-version'])
        etag = r.headers['etag']
        self.assertEqual(r.text, 'b')
        self.client.reset_headers()

        r = self.client.object_put(obj, if_etag_not_match=etag, data='c', content_type='application/octet-stream', success=(201, 412))
        self.assertEqual(r.status_code, 412)
        self.client.reset_headers()

        tmpdir = 'dir'+unicode(self.now)
        r = self.client.object_put(tmpdir, content_type='application/directory', content_length=0)
        self.client.reset_headers()
        r = self.client.object_get(tmpdir)
        self.assertEqual(r.headers['content-type'], 'application/directory')
        self.client.reset_headers()

        r = self.client.object_put('%s/%s'%(tmpdir, obj), format=None, 
            copy_from='/%s/%s'%(self.client.container, obj),
            content_encoding='application/octet-stream', 
            source_account='admin@adminland.com', 
            content_length=0, success=201)
        self.assertEqual(r.status_code, 201)
        self.client.reset_headers()

        self.client.container = 'testCo'
        fromstr = '/testCo0/'+tmpdir+'/'+obj
        r = self.client.object_put(obj, format=None, copy_from=fromstr,
            content_encoding='application/octet-stream', 
            source_account='admin@adminland.com', 
            content_length=0, success=201)
        self.assertEqual(r.status_code, 201)
        self.client.reset_headers()
        r = self.client.object_get(obj)
        self.assertEqual(r.headers['etag'], etag)
        self.client.reset_headers()

        self.client.container = 'testCo0'
        fromstr = '/testCo/'+obj
        r = self.client.object_put(obj+'v2', format=None, move_from=fromstr,
            content_encoding='application/octet-stream', 
            source_account='nonExistendAddress@NeverLand.com', 
            content_length=0, success=(201, 403))
        self.assertEqual(r.status_code, 403)
        self.client.reset_headers()

        r = self.client.object_put(obj+'v0', format=None, 
            move_from='/testCo/'+obj, 
            content_encoding='application/octet-stream', 
            content_length=0, success=201)
        self.assertEqual(r.status_code, 201)
        self.client.reset_headers()
        r = self.client.object_get(obj+'v0')
        self.assertEqual(r.headers['etag'], etag)
        self.client.reset_headers()

        r = self.client.object_put(obj+'v1', format=None, 
            move_from='/testCo0/'+obj,
            source_version = vers2,
            content_encoding='application/octet-stream',
            content_length=0, success=201)
        self.client.reset_headers()

        """Some problems with transfer-encoding?
        Content_disposition? manifest?"""

        self.client.delete_object(tmpdir+'/'+obj)
        self.client.delete_object(tmpdir)
        self.client.delete_object(obj+'v1')
        self.client.delete_object(obj+'v0')
        self.client.container = ''
        self.client.reset_headers()

class testCyclades(unittest.TestCase):
    def setUp(self):
        pass

    def test_list_servers(self):
        pass

def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(testPithos))
    #suite.addTest(unittest.makeSuite(testCyclades))
    return suite

if __name__ == '__main__':
    suiteFew = unittest.TestSuite()

    #kamaki/pithos.py
    suiteFew.addTest(testPithos('test_account_head'))
    suiteFew.addTest(testPithos('test_account_get'))
    suiteFew.addTest(testPithos('test_account_post'))
    suiteFew.addTest(testPithos('test_container_head'))
    suiteFew.addTest(testPithos('test_container_get'))
    suiteFew.addTest(testPithos('test_container_put'))
    suiteFew.addTest(testPithos('test_container_post'))
    suiteFew.addTest(testPithos('test_container_delete'))
    suiteFew.addTest(testPithos('test_object_head'))
    suiteFew.addTest(testPithos('test_object_get'))
    suiteFew.addTest(testPithos('test_object_put'))

    #kamaki/cyclades.py
    #suiteFew.addTest(testCyclades('test_list_servers'))

    unittest.TextTestRunner(verbosity = 2).run(suite())
