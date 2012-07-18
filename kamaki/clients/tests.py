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

from kamaki.clients import pithos
from kamaki.clients import cyclades

class testPithos(unittest.TestCase):
    def setUp(self):
        url = 'http://127.0.0.1:8000/v1'
        token = 'C/yBXmz3XjTFBnujc2biAg=='
        token = 'ac0yH8cQMEZu3M3Mp1MWGA=='
        account = 'admin@adminland.com'
        container=None
        self.client = pithos(url, token, account, container)

    def test_account_head(self):
        r = self.client.account_head()
        self.assertEqual(r.status_code, 204)
        r = self.client.account_head(until='1000000000')
        self.assertEqual(r.status_code, 204)
        datestring = unicode(r.headers['x-account-until-timestamp'])
        self.assertEqual(u'Sun, 09 Sep 2001 01:46:40 GMT', datestring)
        import time
        now = time.mktime(time.gmtime())
        r = self.client.account_head(if_modified_since=now)
        r = self.client.account_head(if_unmodified_since=10000)

    def test_account_get(self):
        r = self.client.account_get()
        self.assertEqual(r.status_code, 200)
        fullLen = len(r.json)
        self.assertEqual(fullLen, 3)
        r = self.client.account_get(limit=1)
        self.assertEqual(len(r.json), 1)
        #Assume there exist at least two containers prefixed 'test'
        r = self.client.account_get(limit=3, marker='test')
        self.assertNotEqual(len(r.json), 0)
        conames = [container['name'] for container in r.json if container['name'].lower().startswith('test')]
        self.assertEqual(len(conames), len(r.json))
        r = self.client.account_get(show_only_shared=True)
        self.assertEqual(len(r.json), 2)
        r = self.client.account_get(until=1342609206)
        self.assertEqual(len(r.json), 2)

    def test_account_post(self):
        r = self.client.account_post()
        self.assertEqual(r.status_code, 202)
        grpName = 'tstgrp'
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
        r = self.client.container_get(format='xml')
        self.assertEqual(r.text.split()[4], 'name="testCo">')
        #meta-check is not that obvious...
        self.client.set_container_meta({'m1':'v1', 'm2':'v2'}
        r = self.client.container_get(meta=[])
        

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

    #kamaki/cyclades.py
    #suiteFew.addTest(testCyclades('test_list_servers'))

    unittest.TextTestRunner(verbosity = 2).run(suite())
