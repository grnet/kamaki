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
        self.c1 = 'c1_'+unicode(self.now)
        self.c2 = 'c2_'+unicode(self.now)
        self.c3 = 'c3_'+unicode(self.now)
        self.client.create_container(self.c1)
        self.client.reset_headers()
        self.client.create_container(self.c2)
        self.client.reset_headers()
        self.client.create_container(self.c3)
        self.client.reset_headers()
        self.makeNewObject(self.c1, 'test')
        self.makeNewObject(self.c2, 'test')
        self.makeNewObject(self.c1, 'test1')
        self.makeNewObject(self.c2, 'test1')
        """Prepare a object to be shared - also its container"""
        self.client.container = self.c1
        self.client.object_post('test', update=True,
            permitions={'read':'someUser'})

    def makeNewObject(self, container, obj):
        self.client.container = container
        self.client.object_put(obj, content_type='application/octet-stream',
            data= obj+' '+container, metadata={'incontainer':container})
        self.client.reset_headers()

    def forceDeleteContainer(self, container):
        self.client.container = container
        r = self.client.list_objects()
        for obj in r:
            name = obj['name']
            self.client.reset_headers()
            self.client.object_delete(name)
            print('Just deleted '+name+' in '+container)
        self.client.reset_headers()
        self.client.container_delete()
        self.client.reset_headers()
        self.container = ''

    def tearDown(self):
        self.forceDeleteContainer(self.c1)
        self.forceDeleteContainer(self.c2)
        self.forceDeleteContainer(self.c3)

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
        self.assertTrue(fullLen > 2)

        r = self.client.account_get(limit=1)
        self.assertEqual(len(r.json), 1)

        r = self.client.account_get(limit=3, marker='c2_')
        conames = [container['name'] for container in r.json if container['name'].lower().startswith('c2_')]
        self.assertTrue(self.c2 in conames)
        self.assertFalse(self.c1 in conames)
        self.client.reset_headers()

        r = self.client.account_get(show_only_shared=True)
        self.assertTrue(self.c1 in [c['name'] for c in r.json])
        self.client.reset_headers()

        r = self.client.account_get(until=1342609206)
        self.assertTrue(len(r.json) <= fullLen)
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
        grpName = 'grp'+unicode(self.now)

        """Method set/del_account_meta and set_account_groupcall account_post internally
        """
        self.client.set_account_group(grpName, ['u1', 'u2'])
        r = self.client.get_account_group()
        self.assertEqual(r['x-account-group-'+grpName], 'u1,u2')
        self.client.del_account_group(grpName)
        r = self.client.get_account_group()
        self.assertTrue(not r.has_key('x-account-group-'+grpName))
        self.client.reset_headers()

        mprefix = 'meta'+unicode(self.now)
        self.client.set_account_meta({mprefix+'1':'v1', mprefix+'2':'v2'})
        r = self.client.get_account_meta()
        self.assertEqual(r['x-account-meta-'+mprefix+'1'], 'v1')
        self.assertEqual(r['x-account-meta-'+mprefix+'2'], 'v2')
        self.client.reset_headers()

        self.client.del_account_meta(mprefix+'1')
        r = self.client.get_account_meta()
        self.assertTrue(not r.has_key('x-account-meta-'+mprefix+'1'))
        self.client.reset_headers()

        self.client.del_account_meta(mprefix+'2')
        r = self.client.get_account_meta()
        self.assertTrue(not r.has_key('x-account-meta-'+mprefix+'2'))
        self.client.reset_headers()

        """Missing testing for quota, versioning, because normally
        you don't have permitions for modified those at account level
        """

    def atest_container_head(self):
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

    def atest_container_get(self):
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
       
    def atest_container_put(self):
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

    def atest_container_post(self):
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

    def atest_container_delete(self):
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

    def atest_object_head(self):
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

    def atest_object_get(self):
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

    def atest_object_put(self):
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
            source_account=self.account,
            content_length=0, success=201)
        self.assertEqual(r.status_code, 201)
        self.client.reset_headers()

        self.client.container = 'testCo'
        fromstr = '/testCo0/'+tmpdir+'/'+obj
        r = self.client.object_put(obj, format=None, copy_from=fromstr,
            content_encoding='application/octet-stream', 
            source_account=self.account,
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

    def atest_object_copy(self):
        self.client.container='testCo0'
        obj = 'obj'+unicode(self.now)

        data= '{"key1":"val1", "key2":"val2"}'
        r = self.client.object_put(obj+'orig', content_type='application/octet-stream',
            data= data, metadata={'mkey1':'mval1', 'mkey2':'mval2'},
            permitions={'read':['accX:groupA', 'u1', 'u2'], 'write':['u2', 'u3']})
        self.client.reset_headers()
        r = self.client.object_copy(obj+'orig', destination = '/'+self.client.container+'/'+obj, ignore_content_type=False, content_type='application/json', 
            metadata={'mkey2':'mval2a', 'mkey3':'mval3'},
            permitions={'write':['u5', 'accX:groupB']})
        self.assertEqual(r.status_code, 201)
        self.client.reset_headers()

        """Check Metadata"""
        r = self.client.object_get(obj)
        self.assertTrue(r.headers.has_key('x-object-meta-mkey1'))
        self.assertEqual(r.headers['x-object-meta-mkey1'], 'mval1')
        self.assertTrue(r.headers.has_key('x-object-meta-mkey2'))
        self.assertEqual(r.headers['x-object-meta-mkey2'], 'mval2a')
        self.assertTrue(r.headers.has_key('x-object-meta-mkey3'))
        self.assertEqual(r.headers['x-object-meta-mkey3'], 'mval3')
        """Check permitions"""
        self.assertFalse('read' in r.headers['x-object-sharing'])
        self.assertFalse('u2' in r.headers['x-object-sharing'])
        self.assertTrue('write' in r.headers['x-object-sharing'])
        self.assertTrue('accx:groupb' in r.headers['x-object-sharing'])
        self.client.reset_headers()

        """Check destination account"""
        r = self.client.object_copy(obj, destination='/testCo/'+obj, content_encoding='utf8',
            content_type='application/json', destination_account='nonExistendAddress@NeverLand.com',
            success=(201, 403))
        self.assertEqual(r.status_code, 403)
        self.client.reset_headers()

        """Check destination being another container and also content_type and content encoding"""
        r = self.client.object_copy(obj, destination='/testCo/'+obj, content_encoding='utf8', content_type='application/json')
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.headers['content-type'], 'application/json; charset=UTF-8')
        self.client.reset_headers()
        r = self.client.container='testCo'
        self.client.delete_object(obj)
        r = self.client.container='testCo0'
        self.client.reset_headers()

        """Check ignore_content_type and content_type"""
        r = self.client.object_get(obj)
        etag = r.headers['etag']
        ctype = r.headers['content-type']
        self.assertEqual(ctype, 'application/json')
        self.client.reset_headers()
        r = self.client.object_copy(obj+'orig', destination = '/'+self.client.container+'/'+obj+'0',
            ignore_content_type=True, content_type='application/json')
        self.assertEqual(r.status_code, 201)
        self.assertNotEqual(r.headers['content-type'], 'application/json')
        self.client.reset_headers()

        """Check if_etag_(not_)match"""
        r = self.client.object_copy(obj, destination='/'+self.client.container+'/'+obj+'1', if_etag_match=etag)
        self.assertEqual(r.status_code, 201)
        self.client.reset_headers()
        r = self.client.object_copy(obj, destination='/'+self.client.container+'/'+obj+'2', if_etag_not_match='lalala')
        self.assertEqual(r.status_code, 201)
        vers2 = r.headers['x-object-version']
        self.client.reset_headers()

        """Check source_version, public and format """
        r = self.client.object_copy(obj+'2', destination='/'+self.client.container+'/'+obj+'3', source_version=vers2, format='xml', public=True)
        self.assertEqual(r.status_code, 201)
        self.assertTrue(r.headers['content-type'].index('xml') > 0)
        self.client.reset_headers()
        r = self.client.object_get(obj+'3')
        self.assertTrue(r.headers.has_key('x-object-public'))
        self.client.reset_headers()

        """Still untested: content_disposition, manifest"""

        self.client.delete_object(obj)
        self.client.delete_object(obj+'0')
        self.client.delete_object(obj+'1')
        self.client.delete_object(obj+'2')
        self.client.delete_object(obj+'3')
        self.client.delete_object(obj+'orig')
        self.client.container = ''

    def atest_object_move(self):
        self.client.container='testCo0'
        obj = 'obj'+unicode(self.now)

        data= '{"key1":"val1", "key2":"val2"}'
        r = self.client.object_put(obj+'orig', content_type='application/octet-stream',
            data= data, metadata={'mkey1':'mval1', 'mkey2':'mval2'},
            permitions={'read':['accX:groupA', 'u1', 'u2'], 'write':['u2', 'u3']})
        self.client.reset_headers()
        r = self.client.object_move(obj+'orig', destination = '/'+self.client.container+'/'+obj, ignore_content_type=False, content_type='application/json', 
            metadata={'mkey2':'mval2a', 'mkey3':'mval3'},
            permitions={'write':['u5', 'accX:groupB']})
        self.assertEqual(r.status_code, 201)
        self.client.reset_headers()

        """Check Metadata"""
        r = self.client.object_get(obj)
        self.assertTrue(r.headers.has_key('x-object-meta-mkey1'))
        self.assertEqual(r.headers['x-object-meta-mkey1'], 'mval1')
        self.assertTrue(r.headers.has_key('x-object-meta-mkey2'))
        self.assertEqual(r.headers['x-object-meta-mkey2'], 'mval2a')
        self.assertTrue(r.headers.has_key('x-object-meta-mkey3'))
        self.assertEqual(r.headers['x-object-meta-mkey3'], 'mval3')
        """Check permitions"""
        self.assertFalse('read' in r.headers['x-object-sharing'])
        self.assertFalse('u2' in r.headers['x-object-sharing'])
        self.assertTrue('write' in r.headers['x-object-sharing'])
        self.assertTrue('accx:groupb' in r.headers['x-object-sharing'])
        self.client.reset_headers()

        """Check destination account"""
        r = self.client.object_move(obj, destination='/testCo/'+obj, content_encoding='utf8',
            content_type='application/json', destination_account='nonExistendAddress@NeverLand.com',
            success=(201, 403))
        self.assertEqual(r.status_code, 403)
        self.client.reset_headers()

        """Check destination being another container and also content_type and content encoding"""
        r = self.client.object_move(obj, destination='/testCo/'+obj,
            content_encoding='utf8', content_type='application/json')
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.headers['content-type'], 'application/json; charset=UTF-8')
        self.client.reset_headers()
        self.client.reset_headers()

        """Check ignore_content_type and content_type"""
        r = self.client.container='testCo'
        r = self.client.object_get(obj)
        etag = r.headers['etag']
        ctype = r.headers['content-type']
        self.assertEqual(ctype, 'application/json')
        self.client.reset_headers()
        r = self.client.object_move(obj, destination = '/testCo0/'+obj,
            ignore_content_type=True, content_type='application/json')
        self.assertEqual(r.status_code, 201)
        self.assertNotEqual(r.headers['content-type'], 'application/json')
        r = self.client.container='testCo0'
        self.client.reset_headers()

        """Check if_etag_(not_)match"""
        r = self.client.object_move(obj, destination='/'+self.client.container+'/'+obj+'0', if_etag_match=etag)
        self.assertEqual(r.status_code, 201)
        self.client.reset_headers()
        r = self.client.object_move(obj+'0', destination='/'+self.client.container+'/'+obj+'1', if_etag_not_match='lalala')
        self.assertEqual(r.status_code, 201)
        self.client.reset_headers()

        """Check public and format """
        r = self.client.object_move(obj+'1', destination='/'+self.client.container+'/'+obj+'2', format='xml', public=True)
        self.assertEqual(r.status_code, 201)
        self.assertTrue(r.headers['content-type'].index('xml') > 0)
        self.client.reset_headers()
        r = self.client.object_get(obj+'2')
        self.assertTrue(r.headers.has_key('x-object-public'))
        self.client.reset_headers()

        """Still untested: content_disposition, manifest"""
        self.client.delete_object(obj+'2')
        self.client.container=''

    def atest_object_post(self):
        self.client.container='testCo0'
        obj = 'obj'+unicode(self.now)
        """create a filesystem file"""
        newf = open(obj, 'w')
        newf.writelines(['ello!\n','This is a test line\n','inside a test file\n'])
        """create a file on container"""
        r = self.client.object_put(obj, content_type='application/octet-stream',
            data= 'H', metadata={'mkey1':'mval1', 'mkey2':'mval2'},
            permitions={'read':['accX:groupA', 'u1', 'u2'], 'write':['u2', 'u3']})
        self.client.reset_headers()

        """Append tests update, content_range, content_type, content_length"""
        newf = open(obj, 'r')
        self.client.append_object(obj, newf)
        self.client.reset_headers()
        r = self.client.object_get(obj)
        self.assertTrue(r.text.startswith('Hello!'))
        self.client.reset_headers()

        """Overwrite tests update, content_type, content_length, content_range"""
        newf.seek(0)
        r = self.client.overwrite_object(obj, 0, 10, newf)
        self.client.reset_headers()
        r = self.client.object_get(obj)
        self.assertTrue(r.text.startswith('ello!'))
        newf.close()
        self.client.reset_headers()
        
        """Truncate tests update, content_range, content_type,
        object_bytes and source_object"""
        r = self.client.truncate_object(obj, 5)
        self.client.reset_headers()
        r = self.client.object_get(obj)
        self.assertEqual(r.text, 'ello!')
        self.client.reset_headers()

        """Check metadata"""
        self.client.set_object_meta(obj, {'mkey2':'mval2a', 'mkey3':'mval3'})
        self.client.reset_headers()
        r = self.client.get_object_meta(obj)
        self.assertTrue(r.has_key('x-object-meta-mkey1'))
        self.assertEqual(r['x-object-meta-mkey1'], 'mval1')
        self.assertTrue(r.has_key('x-object-meta-mkey2'))
        self.assertEqual(r['x-object-meta-mkey2'], 'mval2a')
        self.assertTrue(r.has_key('x-object-meta-mkey3'))
        self.assertEqual(r['x-object-meta-mkey3'], 'mval3')
        self.client.reset_headers()
        self.client.del_object_meta('mkey1', obj)
        self.client.reset_headers()
        r = self.client.get_object_meta(obj)
        self.assertFalse(r.has_key('x-object-meta-mkey1'))
        self.client.reset_headers()

        """Check permitions"""
        self.client.set_object_sharing(obj, read_permition=['u4', 'u5'], write_permition=['u4'])
        self.client.reset_headers()
        r = self.client.get_object_sharing(obj)
        self.assertTrue(r.has_key('x-object-sharing'))
        val = r['x-object-sharing']
        self.assertTrue(val.index('read') < val.index('u5') < val.index('write') < val.index('u4'))
        self.client.reset_headers()
        self.client.del_object_sharing(obj)
        r = self.client.get_object_sharing(obj)
        self.assertFalse(r.has_key('x-object-sharing'))
        self.client.reset_headers()

        """Check publish"""
        self.client.publish_object(obj)
        self.client.reset_headers()
        r = self.client.get_object_info(obj)
        self.assertTrue(r.has_key('x-object-public'))
        self.client.reset_headers()
        self.client.unpublish_object(obj)
        self.client.reset_headers()
        r = self.client.get_object_info(obj)
        self.assertFalse(r.has_key('x-object-public'))
        self.client.reset_headers()

        """Check if_etag_(not)match"""
        etag = r['etag']
        r = self.client.object_post(obj, update=True, public=True,
            if_etag_not_match=etag, success=(412,202,204))
        self.assertEqual(r.status_code, 412)
        self.client.reset_headers()
        self.client.object_post(obj, update=True, public=True,
            if_etag_match=etag, content_encoding='application/json')
        self.client.reset_headers()
        r = self.client.get_object_info(obj)
        helloVersion = r['x-object-version']
        self.assertTrue(r.has_key('x-object-public'))
        self.assertEqual(r['content-encoding'], 'application/json')
        self.client.reset_headers()

        """Check source_version and source_account"""
        r = self.client.object_post(obj, update=True, content_type='application/octet-srteam',
            content_length=5, content_range='bytes 1-5/*', source_object='/testCo0/'+obj,
            source_account='thisAccountWillNeverExist@adminland.com', source_version=helloVersion, data='12345',
            success=(403, 202, 204))
        self.assertEqual(r.status_code, 403)
        self.client.reset_headers()
        r = self.client.object_post(obj, update=True, content_type='application/octet-srteam',
            content_length=5, content_range='bytes 1-5/*', source_object='/testCo0/'+obj,
            source_account='thisAccountWillNeverExist@adminland.com', source_version=helloVersion, data='12345')
        self.client.reset_headers()
        r = self.client.object_get(obj)
        self.assertEqual(r.text, 'eello!')
        self.client.reset_headers()

        """We need to check transfer_encoding, content_disposition, manifest """

        self.client.object_delete(obj)
        os.remove(obj)
        self.client.container=''

    def atest_object_delete(self):
        self.client.container='testCo0'
        obj = 'obj'+unicode(self.now)
        """create a file on container"""
        r = self.client.object_put(obj, content_type='application/octet-stream',
            data= 'H', metadata={'mkey1':'mval1', 'mkey2':'mval2'},
            permitions={'read':['accX:groupA', 'u1', 'u2'], 'write':['u2', 'u3']})
        self.client.reset_headers()

        """Check with false until"""
        r = self.client.object_delete(obj, until=1000000)
        self.client.reset_headers()
        r = self.client.object_get(obj, success=(200, 404))
        self.assertEqual(r.status_code, 200)

        """Check normal case"""
        r = self.client.object_delete(obj)
        self.client.reset_headers()
        self.assertEqual(r.status_code, 204)
        r = self.client.object_get(obj, success=(200, 404))
        self.assertEqual(r.status_code, 404)

        self.client.container = ''

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
    """
    suiteFew.addTest(testPithos('test_container_head'))
    suiteFew.addTest(testPithos('test_container_get'))
    suiteFew.addTest(testPithos('test_container_put'))
    suiteFew.addTest(testPithos('test_container_post'))
    suiteFew.addTest(testPithos('test_container_delete'))
    suiteFew.addTest(testPithos('test_object_head'))
    suiteFew.addTest(testPithos('test_object_get'))
    suiteFew.addTest(testPithos('test_object_put'))
    suiteFew.addTest(testPithos('test_object_copy'))
    suiteFew.addTest(testPithos('test_object_move'))
    suiteFew.addTest(testPithos('test_object_post'))
    suiteFew.addTest(testPithos('test_object_delete'))
    """

    #kamaki/cyclades.py
    #suiteFew.addTest(testCyclades('test_list_servers'))

    unittest.TextTestRunner(verbosity = 2).run(suite())
