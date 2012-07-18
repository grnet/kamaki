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
        account = 'admin@adminland.com'
        container=None
        self.client = pithos(url, token, account, container)

    def test_account_head(self):
        r = self.client.account_head()
        self.assertEqual(r.status_code, 204)
        r = self.client.account_head(until='99999999', if_modified_since='1234', if_unmodified_since='5678')
        self.assertEqual(r.status_code, 204)
        print(unicode(r.headers['x-account-until-timestamp']))

class testCyclades(unittest.TestCase):
    def setUp(self):
        pass

    def test_list_servers(self):
        pass

def suite():
    suite = unittest.TestSuite()
    #suite.addTest(unittest.makeSuite(testCyclades))
    suite.addTest(unittest.makeSuite(testPithos))
    return suite

if __name__ == '__main__':
    suiteFew = unittest.TestSuite()

    #kamaki/pithos.py
    suiteFew.addTest(testPithos('test_account_head'))

    #kamaki/cyclades.py
    #suiteFew.addTest(testCyclades('test_list_servers'))

    unittest.TextTestRunner(verbosity = 2).run(suite())
