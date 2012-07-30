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
import time, datetime, os
from shutil import copyfile

from kamaki.clients import pithos, cyclades, ClientError

class testPithos(unittest.TestCase):
    """Set up a Pithos+ thorough test"""
    def setUp(self):
        url = 'http://127.0.0.1:8000/v1'
        token = 'C/yBXmz3XjTFBnujc2biAg=='
        token = 'ac0yH8cQMEZu3M3Mp1MWGA=='
        account = 'admin@adminland.com'
        self.fname = None
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
        self.now_unformated = datetime.datetime.utcnow()
        self.makeNewObject(self.c1, 'test1')
        self.makeNewObject(self.c2, 'test1')
        """Prepare an object to be shared - also its container"""
        self.client.container = self.c1
        self.client.object_post('test', update=True,
            permitions={'read':'someUser'})
        self.makeNewObject(self.c1, 'another.test')

    def makeNewObject(self, container, obj):
        self.client.container = container
        self.client.object_put(obj, content_type='application/octet-stream',
            data= 'file '+obj+' that lives in '+container,
            metadata={'incontainer':container})
        self.client.reset_headers()

    def forceDeleteContainer(self, container):
        self.client.container = container
        r = self.client.list_objects()
        for obj in r:
            name = obj['name']
            self.client.reset_headers()
            self.client.object_delete(name)
        self.client.reset_headers()
        self.client.container_delete()
        self.client.reset_headers()
        self.container = ''

    def tearDown(self):
        """Destroy test cases"""
        if self.fname is not None:
            try:
                os.remove(self.fname)
            except OSError:
                pass
            self.fname = None
        self.forceDeleteContainer(self.c1)
        self.forceDeleteContainer(self.c2)
        try:
            self.forceDeleteContainer(self.c3)
        except ClientError:
            pass
        self.client.container=''

    def test_account_head(self):
        """Test account_HEAD"""
        r = self.client.account_head()
        self.assertEqual(r.status_code, 204)
        r = self.client.account_head(until='1000000000')
        self.assertEqual(r.status_code, 204)
        datestring = unicode(r.headers['x-account-until-timestamp'])
        self.assertEqual(u'Sun, 09 Sep 2001 01:46:40 GMT', datestring)
        self.client.reset_headers()

        """Check if(un)modified_since"""
        for format in self.client.DATE_FORMATS:
            now_formated = self.now_unformated.strftime(format)
            r1 = self.client.account_head(if_modified_since=now_formated, success=(204, 304, 412))
            self.client.reset_headers()
            r2 = self.client.account_head(if_unmodified_since=now_formated, success=(204, 304, 412))
            self.client.reset_headers()
            self.assertNotEqual(r1.status_code, r2.status_code)

    def test_account_get(self):
        """Test account_GET"""
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

        """Check if(un)modified_since"""
        for format in self.client.DATE_FORMATS:
            now_formated = self.now_unformated.strftime(format)
            r1 = self.client.account_get(if_modified_since=now_formated, success=(200, 304, 412))
            self.client.reset_headers()
            r2 = self.client.account_get(if_unmodified_since=now_formated, success=(200, 304, 412))
            self.client.reset_headers()
            self.assertNotEqual(r1.status_code, r2.status_code)

    def test_account_post(self):
        """Test account_POST"""
        r = self.client.account_post()
        self.assertEqual(r.status_code, 202)
        grpName = 'grp'+unicode(self.now)

        """Method set/del_account_meta and set_account_groupcall use account_post internally
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
        you don't have permitions to modify those at account level
        """

    def test_container_head(self):
        """Test container_HEAD"""
        self.client.container = self.c1

        r = self.client.container_head()
        self.assertEqual(r.status_code, 204)

        """Check until"""
        r = self.client.container_head(until=1000000, success=(204, 404))
        self.assertEqual(r.status_code, 404)

        """Check and if(un)modified_since"""
        for format in self.client.DATE_FORMATS:
            now_formated = self.now_unformated.strftime(format)
            self.client.reset_headers()
            r1 = self.client.container_head(if_modified_since=now_formated, success=(204, 304, 412))
            self.client.reset_headers()
            r2 = self.client.container_head(if_unmodified_since=now_formated, success=(204, 304, 412))
            self.client.reset_headers()
            self.assertNotEqual(r1.status_code, r2.status_code)

    def test_container_get(self):
        """Test container_GET"""
        self.client.container = self.c1

        r = self.client.container_get()
        self.assertEqual(r.status_code, 200)
        fullLen = len(r.json)

        r = self.client.container_get(prefix='test')
        lalobjects = [obj for obj in r.json if obj['name'].startswith('test')]
        self.assertTrue(len(r.json) > 1)
        self.assertEqual(len(r.json), len(lalobjects))
        self.client.reset_headers()

        r = self.client.container_get(limit=1)
        self.assertEqual(len(r.json), 1)
        self.client.reset_headers()

        r = self.client.container_get(marker='another')
        self.assertTrue(len(r.json) > 1)
        neobjects = [obj for obj in r.json if obj['name'] > 'another']
        self.assertEqual(len(r.json), len(neobjects))
        self.client.reset_headers()

        r = self.client.container_get(prefix='another.test', delimiter='.')
        self.assertTrue(fullLen > len(r.json))
        self.client.reset_headers()

        r = self.client.container_get(path='/')
        self.assertEqual(fullLen, len(r.json))
        self.client.reset_headers()

        r = self.client.container_get(format='xml')
        self.assertEqual(r.text.split()[4], 'name="'+self.c1+'">')
        self.client.reset_headers()

        r = self.client.container_get(meta=['incontainer'])
        self.assertTrue(len(r.json) > 0)
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

        """Check and if(un)modified_since"""
        for format in self.client.DATE_FORMATS:
            now_formated = self.now_unformated.strftime(format)
            self.client.reset_headers()
            r1 = self.client.container_get(if_modified_since=now_formated, success=(200, 304, 412))
            self.client.reset_headers()
            r2 = self.client.container_get(if_unmodified_since=now_formated, success=(200, 304, 412))
            self.client.reset_headers()
            self.assertNotEqual(r1.status_code, r2.status_code)
            self.client.reset_headers()
       
    def test_container_put(self):
        """Test container_PUT"""
        self.client.container = self.c2

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

    def test_container_post(self):
        """Test container_POST"""
        self.client.container = self.c2

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

        """put_block uses content_type and content_length to
        post blocks of data 2 container. All that in upload_object"""
        """Change a file at fs"""
        self.fname = 'f'+unicode(self.now)
        copyfile('pirifi.237M', self.fname)
        newf = open(self.fname, 'a')
        newf.write('add:'+unicode(self.now)+'\n')
        newf.close()
        """Upload it at a directory in container"""
        self.client.create_directory('dir')
        self.client.reset_headers()
        newf = open(self.fname, 'r')
        self.client.upload_object('/dir/sample.file', newf)
        self.client.reset_headers()
        newf.close()
        """Check if file has been uploaded"""
        r = self.client.get_object_info('/dir/sample.file')
        self.assertTrue(int(r['content-length']) > 248209936)

        """WTF is tranfer_encoding? What should I check about th** s**t? """
        #TODO

        """Check update=False"""
        r = self.client.object_post('test', update=False, metadata={'newmeta':'newval'})
        self.client.reset_headers()
        r = self.client.get_object_info('test')
        self.client.reset_headers()
        self.assertTrue(r.has_key('x-object-meta-newmeta'))
        self.assertFalse(r.has_key('x-object-meta-incontainer'))

        r = self.client.del_container_meta('m2')
        self.client.reset_headers()

    def test_container_delete(self):
        """Test container_DELETE"""

        """Fail to delete a non-empty container"""
        self.client.container = self.c2
        r = self.client.container_delete(success=409)
        self.assertEqual(r.status_code, 409)
        self.client.reset_headers()

        """Fail to delete c3 (empty) container"""
        self.client.container = self.c3
        r = self.client.container_delete(until='1000000000')
        self.assertEqual(r.status_code, 204)
        self.client.reset_headers()

        """Delete c3 (empty) container"""
        r = self.client.container_delete()
        self.assertEqual(r.status_code, 204)
        self.client.reset_headers()

    def test_object_head(self):
        """Test object_HEAD"""
        self.client.container = self.c2
        obj = 'test'

        r = self.client.object_head(obj)
        self.assertEqual(r.status_code, 200)
        etag = r.headers['etag']

        r = self.client.object_head(obj, version=40)
        self.assertEqual(r.headers['x-object-version'], '40')
        self.client.reset_headers()

        r = self.client.object_head(obj, if_etag_match=etag)
        self.assertEqual(r.status_code, 200)
        self.client.reset_headers()
        r = self.client.object_head(obj, if_etag_not_match=etag, success=(200, 412, 304))
        self.assertNotEqual(r.status_code, 200)

        r = self.client.object_head(obj, version=40, if_etag_match=etag, success=412)
        self.assertEqual(r.status_code, 412)
        self.client.reset_headers()

        """Check and if(un)modified_since"""
        for format in self.client.DATE_FORMATS:
            now_formated = self.now_unformated.strftime(format)
            self.client.reset_headers()
            r1 = self.client.object_head(obj, if_modified_since=now_formated, success=(200, 304, 412))
            self.client.reset_headers()
            r2 = self.client.object_head(obj, if_unmodified_since=now_formated, success=(200, 304, 412))
            self.client.reset_headers()
            self.assertNotEqual(r1.status_code, r2.status_code)
            self.client.reset_headers()

    def test_object_get(self):
        """Test object_GET"""
        self.client.container = self.c1
        obj = 'test'

        r = self.client.object_get(obj)
        self.assertEqual(r.status_code, 200)

        osize = int(r.headers['content-length'])
        etag = r.headers['etag']

        r = self.client.object_get(obj, hashmap=True)
        self.assertTrue(r.json.has_key('hashes') \
            and r.json.has_key('block_hash') \
            and r.json.has_key('block_size') \
            and r.json.has_key('bytes'))

        r = self.client.object_get(obj, format='xml', hashmap=True)
        self.assertEqual(len(r.text.split('hash>')), 3)
        self.client.reset_headers()

        rangestr = 'bytes=%s-%s'%(osize/3, osize/2)
        r = self.client.object_get(obj, data_range=rangestr, success=(200, 206))
        partsize = int(r.headers['content-length'])
        self.assertTrue(0 < partsize and partsize <= 1+osize/3)
        self.client.reset_headers()

        rangestr = 'bytes=%s-%s'%(osize/3, osize/2)
        r = self.client.object_get(obj, data_range=rangestr, if_range=True, success=(200, 206))
        partsize = int(r.headers['content-length'])
        self.assertTrue(0 < partsize and partsize <= 1+osize/3)
        self.client.reset_headers()

        r = self.client.object_get(obj, if_etag_match=etag)
        self.assertEqual(r.status_code, 200)
        self.client.reset_headers()

        r = self.client.object_get(obj, if_etag_not_match=etag+'LALALA')
        self.assertEqual(r.status_code, 200)
        self.client.reset_headers()

        """Check and if(un)modified_since"""
        for format in self.client.DATE_FORMATS:
            now_formated = self.now_unformated.strftime(format)
            self.client.reset_headers()
            r1 = self.client.object_get(obj, if_modified_since=now_formated, success=(200, 304, 412))
            self.client.reset_headers()
            r2 = self.client.object_get(obj, if_unmodified_since=now_formated, success=(200, 304, 412))
            self.client.reset_headers()
            self.assertNotEqual(r1.status_code, r2.status_code)
            self.client.reset_headers()

    def test_object_put(self):
        """test object_PUT"""

        self.client.container = self.c2
        obj='another.test'

        """create the object"""
        r = self.client.object_put(obj, data='a', content_type='application/octer-stream',
            permitions={'read':['accX:groupA', 'u1', 'u2'], 'write':['u2', 'u3']},
            metadata={'key1':'val1', 'key2':'val2'}, content_encoding='UTF-8',
            content_disposition='attachment; filename="fname.ext"')
        self.assertEqual(r.status_code, 201)
        etag = r.headers['etag']
        self.client.reset_headers()

        """Check content-disposition"""
        r = self.client.get_object_info(obj)
        self.assertTrue(r.has_key('content-disposition'))

        """Check permitions"""
        r = self.client.get_object_sharing(obj)
        self.assertTrue('accx:groupa' in r['read'])
        self.assertTrue('u1' in r['read'])
        self.assertTrue('u2' in r['write'])
        self.assertTrue('u3' in r['write'])
        self.client.reset_headers()

        """Check metadata"""
        r = self.client.get_object_meta(obj)
        self.assertEqual(r['key1'], 'val1')
        self.assertEqual(r['key2'], 'val2')
        self.client.reset_headers()

        """Check public and if_etag_match"""
        r = self.client.object_put(obj, if_etag_match=etag, data='b',
            content_type='application/octet-stream', public=True)
        self.client.reset_headers()
        r = self.client.object_get(obj)
        self.client.reset_headers()
        self.assertTrue(r.headers.has_key('x-object-public'))
        vers2 = int(r.headers['x-object-version'])
        etag = r.headers['etag']
        self.assertEqual(r.text, 'b')
        self.client.reset_headers()

        """Check if_etag_not_match"""
        r = self.client.object_put(obj, if_etag_not_match=etag, data='c',
            content_type='application/octet-stream', success=(201, 412))
        self.assertEqual(r.status_code, 412)
        self.client.reset_headers()

        """Check content_type and content_length"""
        tmpdir = 'dir'+unicode(self.now)
        r = self.client.object_put(tmpdir, content_type='application/directory',
            content_length=0)
        self.client.reset_headers()
        r = self.client.get_object_info(tmpdir)
        self.assertEqual(r['content-type'], 'application/directory')
        self.client.reset_headers()

        """Check copy_from, content_encoding"""
        r = self.client.object_put('%s/%s'%(tmpdir, obj), format=None, 
            copy_from='/%s/%s'%(self.client.container, obj),
            content_encoding='application/octet-stream', 
            source_account=self.client.account,
            content_length=0, success=201)
        self.assertEqual(r.status_code, 201)
        self.client.reset_headers()

        """Check cross-container copy_from, content_encoding"""
        self.client.container = self.c1
        fromstr = '/'+self.c2+'/'+tmpdir+'/'+obj
        r = self.client.object_put(obj, format=None, copy_from=fromstr,
            content_encoding='application/octet-stream', 
            source_account=self.client.account,
            content_length=0, success=201)
        self.assertEqual(r.status_code, 201)
        self.client.reset_headers()
        r = self.client.get_object_info(obj)
        self.assertEqual(r['etag'], etag)
        self.client.reset_headers()

        """Check source_account"""
        self.client.container = self.c2
        fromstr = '/'+self.c1+'/'+obj
        r = self.client.object_put(obj+'v2', format=None, move_from=fromstr,
            content_encoding='application/octet-stream', 
            source_account='nonExistendAddress@NeverLand.com', 
            content_length=0, success=(201, 403))
        self.assertEqual(r.status_code, 403)
        self.client.reset_headers()

        """Check cross-container move_from"""
        r = self.client.object_put(obj+'v0', format=None, 
            move_from='/'+self.c1+'/'+obj, 
            content_encoding='application/octet-stream', 
            content_length=0, success=201)
        self.assertEqual(r.status_code, 201)
        self.client.reset_headers()
        r = self.client.get_object_info(obj+'v0')
        self.assertEqual(r['etag'], etag)
        self.client.reset_headers()

        """Check move_from"""
        r = self.client.object_put(obj+'v1', format=None, 
            move_from='/'+self.c2+'/'+obj,
            source_version = vers2,
            content_encoding='application/octet-stream',
            content_length=0, success=201)
        self.client.reset_headers()

        """Check manifest"""
        mobj = 'manifest.test'
        txt = ''
        for i in range(10):
            txt += '%s'%i
            r = self.client.object_put('%s/%s'%(mobj, i), data='%s'%i,
                content_encoding='application/octet-stream',
                content_length=1, success=201)
            self.client.reset_headers()
        self.client.object_put(mobj, content_length=0,
            manifest='%s/%s'%(self.client.container, mobj))
        self.client.reset_headers()
        r = self.client.object_get(mobj)
        self.assertEqual(r.text, txt)
        self.client.reset_headers()

        """Some problems with transfer-encoding?"""

    def test_object_copy(self):
        """test object_COPY"""
        self.client.container=self.c2
        obj = 'test2'

        data= '{"key1":"val1", "key2":"val2"}'
        r = self.client.object_put(obj+'orig', content_type='application/octet-stream',
            data= data, metadata={'mkey1':'mval1', 'mkey2':'mval2'},
            permitions={
                'read':['accX:groupA', 'u1', 'u2'],
                'write':['u2', 'u3']},
            content_disposition='attachment; filename="fname.ext"')
        self.client.reset_headers()
        r = self.client.object_copy(obj+'orig',
            destination = '/'+self.client.container+'/'+obj,
            ignore_content_type=False, content_type='application/json', 
            metadata={'mkey2':'mval2a', 'mkey3':'mval3'},
            permitions={'write':['u5', 'accX:groupB']})
        self.assertEqual(r.status_code, 201)
        self.client.reset_headers()

        """Check content-disposition"""
        r = self.client.get_object_info(obj)
        self.assertTrue(r.has_key('content-disposition'))

        """Check Metadata"""
        r = self.client.get_object_meta(obj)
        self.assertEqual(r['mkey1'], 'mval1')
        self.assertEqual(r['mkey2'], 'mval2a')
        self.assertEqual(r['mkey3'], 'mval3')
        self.client.reset_headers()

        """Check permitions"""
        r = self.client.get_object_sharing(obj)
        self.assertFalse(r.has_key('read') or 'u2' in r['write'])
        self.assertTrue('accx:groupb' in r['write'])
        self.client.reset_headers()

        """Check destination account"""
        r = self.client.object_copy(obj, destination='/%s/%s'%(self.c1,obj), content_encoding='utf8',
            content_type='application/json', destination_account='nonExistendAddress@NeverLand.com',
            success=(201, 403))
        self.assertEqual(r.status_code, 403)
        self.client.reset_headers()

        """Check destination being another container
        and also content_type and content encoding"""
        r = self.client.object_copy(obj, destination='/%s/%s'%(self.c1,obj),
            content_encoding='utf8', content_type='application/json')
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.headers['content-type'], 'application/json; charset=UTF-8')
        self.client.reset_headers()

        """Check ignore_content_type and content_type"""
        r = self.client.object_get(obj)
        etag = r.headers['etag']
        ctype = r.headers['content-type']
        self.assertEqual(ctype, 'application/json')
        self.client.reset_headers()
        r = self.client.object_copy(obj+'orig',
            destination = '/'+self.client.container+'/'+obj+'0',
            ignore_content_type=True, content_type='application/json')
        self.assertEqual(r.status_code, 201)
        self.assertNotEqual(r.headers['content-type'], 'application/json')
        self.client.reset_headers()

        """Check if_etag_(not_)match"""
        r = self.client.object_copy(obj,
            destination='/'+self.client.container+'/'+obj+'1', if_etag_match=etag)
        self.assertEqual(r.status_code, 201)
        self.client.reset_headers()
        r = self.client.object_copy(obj,
            destination='/'+self.client.container+'/'+obj+'2', if_etag_not_match='lalala')
        self.assertEqual(r.status_code, 201)
        vers2 = r.headers['x-object-version']
        self.client.reset_headers()

        """Check source_version, public and format """
        r = self.client.object_copy(obj+'2', destination='/'+self.client.container+'/'+obj+'3', source_version=vers2, format='xml', public=True)
        self.assertEqual(r.status_code, 201)
        self.assertTrue(r.headers['content-type'].index('xml') > 0)
        self.client.reset_headers()
        r = self.client.get_object_info(obj+'3')
        self.assertTrue(r.has_key('x-object-public'))
        self.client.reset_headers()

    def test_object_move(self):
        """Test object_MOVE"""
        self.client.container= self.c2
        obj = 'test2'

        data= '{"key1":"val1", "key2":"val2"}'
        r = self.client.object_put(obj+'orig', content_type='application/octet-stream',
            data= data, metadata={'mkey1':'mval1', 'mkey2':'mval2'},
            permitions={'read':['accX:groupA', 'u1', 'u2'], 'write':['u2', 'u3']})
        self.client.reset_headers()
        r = self.client.object_move(obj+'orig', destination = '/'+self.client.container+'/'+obj,
            ignore_content_type=False, content_type='application/json', 
            metadata={'mkey2':'mval2a', 'mkey3':'mval3'},
            permitions={'write':['u5', 'accX:groupB']})
        self.assertEqual(r.status_code, 201)
        self.client.reset_headers()

        """Check Metadata"""
        r = self.client.get_object_meta(obj)
        self.assertEqual(r['mkey1'], 'mval1')
        self.assertEqual(r['mkey2'], 'mval2a')
        self.assertEqual(r['mkey3'], 'mval3')
        self.client.reset_headers()

        """Check permitions"""
        r = self.client.get_object_sharing(obj)
        self.assertFalse(r.has_key('read'))
        self.assertTrue('u5' in r['write'])
        self.assertTrue('accx:groupb' in r['write'])
        self.client.reset_headers()

        """Check destination account"""
        r = self.client.object_move(obj, destination='/%s/%s'%(self.c1,obj), content_encoding='utf8',
            content_type='application/json', destination_account='nonExistendAddress@NeverLand.com',
            success=(201, 403))
        self.assertEqual(r.status_code, 403)
        self.client.reset_headers()

        """Check destination being another container and also
        content_type, content_disposition and content encoding"""
        r = self.client.object_move(obj, destination='/%s/%s'%(self.c1,obj),
            content_encoding='utf8', content_type='application/json',
            content_disposition='attachment; filename="fname.ext"')
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.headers['content-type'], 'application/json; charset=UTF-8')
        self.client.reset_headers()
        r = self.client.container=self.c1
        r = self.client.get_object_info(obj)
        self.assertTrue(r.has_key('content-disposition') and 'fname.ext' in r['content-disposition'])
        etag = r['etag']
        ctype = r['content-type']
        self.assertEqual(ctype, 'application/json')
        self.client.reset_headers()

        """Check ignore_content_type and content_type"""
        r = self.client.object_move(obj, destination = '/%s/%s'%(self.c2,obj),
            ignore_content_type=True, content_type='application/json')
        self.assertEqual(r.status_code, 201)
        self.assertNotEqual(r.headers['content-type'], 'application/json')
        self.client.reset_headers()

        """Check if_etag_(not_)match"""
        r = self.client.container=self.c2
        r = self.client.object_move(obj, destination='/'+self.client.container+'/'+obj+'0',
            if_etag_match=etag)
        self.assertEqual(r.status_code, 201)
        self.client.reset_headers()
        r = self.client.object_move(obj+'0', destination='/'+self.client.container+'/'+obj+'1',
            if_etag_not_match='lalala')
        self.assertEqual(r.status_code, 201)
        self.client.reset_headers()

        """Check public and format """
        r = self.client.object_move(obj+'1', destination='/'+self.client.container+'/'+obj+'2',
            format='xml', public=True)
        self.assertEqual(r.status_code, 201)
        self.assertTrue(r.headers['content-type'].index('xml') > 0)
        self.client.reset_headers()
        r = self.client.get_object_info(obj+'2')
        self.assertTrue(r.has_key('x-object-public'))
        self.client.reset_headers()

    def test_object_post(self):
        """Test object_POST"""
        self.client.container=self.c2
        obj = 'test2'
        """create a filesystem file"""
        self.fname = obj
        newf = open(self.fname, 'w')
        newf.writelines(['ello!\n','This is a test line\n','inside a test file\n'])
        newf.close()
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
        self.assertEqual(r['mkey1'], 'mval1')
        self.assertEqual(r['mkey2'], 'mval2a')
        self.assertEqual(r['mkey3'], 'mval3')
        self.client.reset_headers()
        self.client.del_object_meta('mkey1', obj)
        self.client.reset_headers()
        r = self.client.get_object_meta(obj)
        self.assertFalse(r.has_key('mkey1'))
        self.client.reset_headers()

        """Check permitions"""
        self.client.set_object_sharing(obj,
            read_permition=['u4', 'u5'], write_permition=['u4'])
        self.client.reset_headers()
        r = self.client.get_object_sharing(obj)
        self.assertTrue(r.has_key('read'))
        self.assertTrue('u5' in r['read'])
        self.assertTrue(r.has_key('write'))
        self.assertTrue('u4' in r['write'])
        self.client.reset_headers()
        self.client.del_object_sharing(obj)
        r = self.client.get_object_sharing(obj)
        self.assertTrue(len(r) == 0)
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

        """Check source_version and source_account and content_disposition"""
        r = self.client.object_post(obj, update=True, content_type='application/octet-srteam',
            content_length=5, content_range='bytes 1-5/*', source_object='/%s/%s'%(self.c2,obj),
            source_account='thisAccountWillNeverExist@adminland.com',
            source_version=helloVersion, data='12345', success=(403, 202, 204))
        self.assertEqual(r.status_code, 403)
        self.client.reset_headers()
        r = self.client.object_post(obj, update=True, content_type='application/octet-srteam',
            content_length=5, content_range='bytes 1-5/*', source_object='/%s/%s'%(self.c2,obj),
            source_account=self.client.account, source_version=helloVersion, data='12345',
            content_disposition='attachment; filename="fname.ext"')
        self.client.reset_headers()
        r = self.client.object_get(obj)
        self.assertEqual(r.text, 'eello!')
        self.assertTrue(r.headers.has_key('content-disposition')
            and 'fname.ext' in r.headers['content-disposition'])
        self.client.reset_headers()

        """Check manifest"""
        mobj = 'manifest.test'
        txt = ''
        for i in range(10):
            txt += '%s'%i
            r = self.client.object_put('%s/%s'%(mobj, i), data='%s'%i,
                content_encoding='application/octet-stream',
                content_length=1, success=201)
            self.client.reset_headers()
        self.client.object_put(mobj, content_length=0)
        self.client.reset_headers()
        r = self.client.object_post(mobj, manifest='%s/%s'%(self.client.container, mobj))
        self.client.reset_headers()
        r = self.client.object_get(mobj)
        self.assertEqual(r.text, txt)
        self.client.reset_headers()

        """We need to check transfer_encoding """

    def test_object_delete(self):
        """Test object_DELETE"""
        self.client.container=self.c2
        obj = 'test2'
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
    suiteFew.addTest(testPithos('test_object_copy'))
    suiteFew.addTest(testPithos('test_object_move'))
    suiteFew.addTest(testPithos('test_object_post'))
    suiteFew.addTest(testPithos('test_object_delete'))

    #kamaki/cyclades.py
    #suiteFew.addTest(testCyclades('test_list_servers'))

    unittest.TextTestRunner(verbosity = 2).run(suite())
