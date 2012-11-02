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

import gevent
import gevent.monkey
# Monkey-patch everything for gevent early on
gevent.monkey.patch_all()
import gevent.pool

import unittest
import sys
from StringIO import StringIO
from time import sleep

from kamaki.clients.connection.kamakicon import KamakiHTTPConnection


class testKamakiCon(unittest.TestCase):
    def setUp(self):
        self.async_pool = None
        self.conn1 = KamakiHTTPConnection()
        self.conn2 = KamakiHTTPConnection()
        self.conn3 = KamakiHTTPConnection()
        self.conn4 = KamakiHTTPConnection()
        account = 'saxtouri@grnet.gr'

        self.conn1.url =\
            'https://pithos.okeanos.io/v1/%s/pithos?path=files' % account
        self.conn1.set_header('X-Auth-Token', '0TpoyAXqJSPxLdDuZHiLOA==')
        self.conn2.url = 'https://pithos.okeanos.io/v1/%s/pithos' % account
        self.conn2.set_header('X-Auth-Token', '0TpoyAXqJSPxLdDuZHiLOA==')
        self.conn3.url =\
            'https://pithos.okeanos.io/v1/%s/pithos?path=subdir' % account
        self.conn3.set_header('X-Auth-Token', '0TpoyAXqJSPxLdDuZHiLOA==')
        self.conn4.url = 'https://pithos.okeanos.io/v1/%s' % account
        self.conn4.set_header('X-Auth-Token', '0TpoyAXqJSPxLdDuZHiLOA==')

    def tearDown(self):
        pass

    def _get_async_content(self, con, **kwargs):
        class SilentGreenlet(gevent.Greenlet):
            def _report_error(self, exc_info):
                _stderr = None
                try:
                    _stderr = sys._stderr
                    sys.stderr = StringIO()
                    gevent.Greenlet._report_error(self, exc_info)
                finally:
                    sys.stderr = _stderr
        POOL_SIZE = 2
        if self.async_pool is None:
            self.async_pool = gevent.pool.Pool(size=POOL_SIZE)
        g = SilentGreenlet(self._get_content_len, con, **kwargs)
        self.async_pool.start(g)
        return g

    def _get_content_len(self, con, **kwargs):
        r = con.perform_request('GET', **kwargs)
        return len(r.content)

    def test_gevents(self):
        h1 = self._get_async_content(self.conn1)
        h2 = self._get_async_content(self.conn2)
        h3 = self._get_async_content(self.conn3)
        h4 = self._get_async_content(self.conn2,
            async_headers={'X-Auth-Token': 'FAKETOKEN'})
        h5 = self._get_async_content(self.conn1)

        while not (h1.ready()\
            and h2.ready()\
            and h3.ready()\
            and h4.ready()\
            and h5.ready()):
            sleep(.000001)

        r1 = h1.value
        r2 = h2.value
        # r3 = h3.value
        r4 = h4.value
        r5 = h5.value
        self.assertEqual(r1, r5)
        self.assertNotEqual(r2, r4)
        #print('1:%s 2:%s 3:%s 4:%s 5:%s'%(r1, r2, r3, r4, r5))

        gevent.joinall([h1, h2, h3, h4, h5])

if __name__ == '__main__':
    suiteFew = unittest.TestSuite()
    suiteFew.addTest(unittest.makeSuite(testKamakiCon))
    unittest.TextTestRunner(verbosity=2).run(suiteFew)
