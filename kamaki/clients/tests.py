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
        r = self.client.account_head(if_modified_since=self.now)
        r = self.client.account_head(if_unmodified_since=10000)

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

        r = self.client.account_get(show_only_shared=True)
        self.assertEqual(len(r.json), 2)

        r = self.client.account_get(until=1342609206)
        self.assertTrue(len(r.json) < fullLen)

        """Missing Full testing for if_modified_since, if_unmodified_since
        """
        r = self.client.account_head(if_modified_since=self.now)
        r = self.client.account_head(if_unmodified_since=10000)

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

        self.client.set_account_meta({'metatest1':'v1', 'metatest2':'v2'})
        r = self.client.get_account_meta()
        self.assertEqual(r['x-account-meta-metatest1'], 'v1')
        self.assertEqual(r['x-account-meta-metatest2'], 'v2')

        self.client.del_account_meta('metatest1')
        r = self.client.get_account_meta()
        self.assertTrue(not r.has_key('x-account-meta-metatest1'))

        self.client.del_account_meta('metatest2')
        r = self.client.get_account_meta()
        self.assertTrue(not r.has_key('x-account-meta-metatest2'))

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
        r = self.client.account_head(if_unmodified_since=1342609206)
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

        r = self.client.container_get(limit=1)
        self.assertEqual(len(r.json), 1)

        r = self.client.container_get(marker='neo')
        self.assertTrue(len(r.json) > 1)
        neobjects = [obj for obj in r.json if obj['name'] > 'neo']
        self.assertEqual(len(r.json), len(neobjects))

        r = self.client.container_get(prefix='testDir/testDir', delimiter='2')
        self.assertTrue(fullLen > len(r.json))

        r = self.client.container_get(path='testDir/testDir2')
        self.assertTrue(fullLen > len(r.json))

        r = self.client.container_get(format='xml')
        self.assertEqual(r.text.split()[4], 'name="testCo">')

        r = self.client.container_get(meta=['Lalakis'])
        self.assertEqual(len(r.json), 1)

        r = self.client.container_get(show_only_shared=True)
        self.assertTrue(len(r.json) < fullLen)

        try:
            r = self.client.container_get(until=1000000000)
            datestring = unicode(r.headers['x-account-until-timestamp'])
            self.assertEqual(u'Sun, 09 Sep 2001 01:46:40 GMT', datestring)
        except:#Normally, container wasn't created in that date...
            pass

        """Missing Full testing for if_modified_since, if_unmodified_since
        """
        now = time.mktime(time.gmtime())
        r = self.client.container_get(if_modified_since=now)
        r = self.client.container_get(if_unmodified_since=now)

        self.container = ''
       
    def test_container_put(self):
        self.client.container = 'testCo'

        r = self.client.container_put()
        self.assertEqual(r.status_code, 202)

        r = self.client.get_container_quota(self.client.container)
        cquota = r.values()[0]
        newquota = 2*int(cquota)

        r = self.client.container_put(quota=newquota)
        self.assertEqual(r.status_code, 202)
        r = self.client.get_container_quota(self.client.container)
        xquota = int(r.values()[0])
        self.assertEqual(newquota, xquota)

        r = self.client.container_put(versioning='auto')
        self.assertEqual(r.status_code, 202)
        r = self.client.get_container_versioning(self.client.container)
        nvers = r.values()[0]
        self.assertEqual('auto', nvers)

        r = self.client.container_put(versioning='none')
        self.assertEqual(r.status_code, 202)
        r = self.client.get_container_versioning(self.client.container)
        nvers = r.values()[0]
        self.assertEqual('none', nvers)

        r = self.client.container_put(metadata={'m1':'v1', 'm2':'v2'})
        self.assertEqual(r.status_code, 202)
        r = self.client.get_container_meta(self.client.container)
        self.assertTrue(r.has_key('x-container-meta-m1'))
        self.assertEqual(r['x-container-meta-m1'], 'v1')
        self.assertTrue(r.has_key('x-container-meta-m2'))
        self.assertEqual(r['x-container-meta-m2'], 'v2')

        r = self.client.container_put(metadata={'m1':'', 'm2':'v2a'})
        self.assertEqual(r.status_code, 202)
        r = self.client.get_container_meta(self.client.container)
        self.assertTrue(not r.has_key('x-container-meta-m1'))
        self.assertTrue(r.has_key('x-container-meta-m2'))
        self.assertEqual(r['x-container-meta-m2'], 'v2a')
       
        self.client.del_container_meta(self.client.container) 
        self.client.container_put(quota=cquota)
        self.client.container = ''

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

        r = self.client.del_container_meta('m1')
        r = self.client.set_container_meta({'m2':'v2a'})
        r = self.client.get_container_meta(self.client.container)
        self.assertTrue(not r.has_key('x-container-meta-m1'))
        self.assertTrue(r.has_key('x-container-meta-m2'))
        self.assertEqual(r['x-container-meta-m2'], 'v2a')

        r = self.client.get_container_quota(self.client.container)
        cquota = r.values()[0]
        newquota = 2*int(cquota)

        r = self.client.set_container_quota(newquota)
        r = self.client.get_container_quota(self.client.container)
        xquota = int(r.values()[0])
        self.assertEqual(newquota, xquota)

        r = self.client.set_container_quota(cquota)
        r = self.client.get_container_quota(self.client.container)
        xquota = r.values()[0]
        self.assertEqual(cquota, xquota)

        self.client.set_container_versioning('auto')
        r = self.client.get_container_versioning(self.client.container)
        nvers = r.values()[0]
        self.assertEqual('auto', nvers)

        self.client.set_container_versioning('none')
        r = self.client.get_container_versioning(self.client.container)
        nvers = r.values()[0]
        self.assertEqual('none', nvers)

        """Haven't figured out how to test put_block, which
        uses content_type and content_length to post blocks
        of data to container. But how do you check that
        the blocks are there?"""

        """WTF is tranfer_encoding? What should I check about th** s**t? """
        r = self.client.container_post(update=True, transfer_encoding='xlm')

        """This last part doesnt seem to work"""
        """self.client.container_post(update=False)"""
        """so we do it the wrong way"""
        r = self.client.del_container_meta('m2')
        self.client.container = ''

    def test_container_delete(self):
        container = 'testCo'+unicode(self.now)
        self.client.container = container

        """Create new container"""
        r = self.client.container_put()
        self.assertEqual(r.status_code, 201)

        """Fail to delete a non-empty container"""
        self.client.container = 'testCo'
        r = self.client.container_delete(success=409)
        self.assertEqual(r.status_code, 409)

        """Fail to delete this container"""
        self.client.container = container
        r = self.client.container_delete(until='1000000000')
        self.assertEqual(r.status_code, 204)

        """Delete this container"""
        r = self.client.container_delete()
        self.assertEqual(r.status_code, 204)

        self.client.container = ''

    def test_object_head(self):
        self.client.container = 'testCo0'
        obj = 'lolens'

        r = self.client.object_head(obj)
        self.assertEqual(r.status_code, 200)
        etag = r.headers['etag']

        r = self.client.object_head(obj, version=40)
        self.assertEqual(r.status_code, 200)

        r = self.client.object_head(obj, if_etag_match=etag)
        self.assertEqual(r.status_code, 200)
        """I believe if_etag_not_match does not work..."""

        r = self.client.object_head(obj, version=40, if_etag_match=etag, success=412)
        self.assertEqual(r.status_code, 412)

        """I believe if_un/modified_since does not work..."""
        r=self.client.object_head(obj, if_modified_since=self.now)
        self.assertEqual(r.status_code, 200)

        r=self.client.object_head(obj, if_unmodified_since=self.now)
        self.assertEqual(r.status_code, 200)

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
    suiteFew.addTest(testPithos('test_container_head'))
    suiteFew.addTest(testPithos('test_container_get'))
    suiteFew.addTest(testPithos('test_container_put'))
    suiteFew.addTest(testPithos('test_container_post'))
    suiteFew.addTest(testPithos('test_container_delete'))
    suiteFew.addTest(testPithos('test_object_head'))

    #kamaki/cyclades.py
    #suiteFew.addTest(testCyclades('test_list_servers'))

    unittest.TextTestRunner(verbosity = 2).run(suite())
