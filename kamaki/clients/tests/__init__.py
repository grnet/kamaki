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

from kamaki.cli.config import Config


def _add_value(foo, value):
    def wrap(self):
        return foo(self, value)
    return wrap


class configuration(object):

    _cnf = None
    _client = ''

    def __init__(self, client='', config_file=None):
        self._cnf = Config(config_file)
        self._client = client

        @property
        def generic_property(self, value):
            """
            :param client: (str) if given, try to get test_client.* and then
            client.*
            :returns: (str) priorities: test_client, client, test, global
            """
            if not hasattr(self, '_%s' % value):
                _acnt = self._cnf.get('test', '%s_%s' % (self._client, value))\
                    or self._cnf.get(self._client, value)\
                    or self._cnf.get('test', value)\
                    or self._cnf.get('global', value)
                if _acnt:
                    setattr(self, '_%s' % value, _acnt)
            return getattr(self, '_%s' % value, None)

        for foo in ('url', 'token'):
            setattr(self, foo, _add_value(generic_property, foo))
