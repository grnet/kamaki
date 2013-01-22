# Copyright 2011-2012 GRNET S.A. All rights reserved.
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
# or implied, of GRNET S.A.command

from traceback import print_stack, print_exc
import logging

from kamaki.clients import ClientError
from kamaki.cli.errors import CLIError, raiseCLIError, CLISyntaxError
from kamaki.cli import _debug, kloger

sendlog = logging.getLogger('clients.send')
datasendlog = logging.getLogger('data.send')
recvlog = logging.getLogger('clients.recv')
datarecvlog = logging.getLogger('data.recv')


class generic(object):

    @classmethod
    def all(this, foo):
        def _raise(self, *args, **kwargs):
            try:
                return foo(self, *args, **kwargs)
            except Exception as e:
                if _debug:
                    print_stack()
                    print_exc(e)
                raiseCLIError(e)
        return _raise


class astakos(object):

    _token_details = [
        'See if token is set: /config get token',
        'If not, set a token:',
        '*  (permanent):    /config set token <token>',
        '*  (temporary):    re-run with <token> parameter']

    @classmethod
    def init(this, foo):
        @generic.all
        def _raise(self, *args, **kwargs):
            r = foo(self, *args, **kwargs)
            try:
                client = getattr(self, 'client')
            except AttributeError as ae:
                raiseCLIError(ae, 'Client setup failure', importance=3)
            if not getattr(client, 'token', False):
                kloger.warning(
                    'No permanent token (try: kamaki config set token <tkn>)')
            if not getattr(client, 'base_url', False):
                raise CLIError('Missing astakos server URL',
                    importance=3,
                    details=['Check if astakos.url is set correctly',
                    'To get astakos url:   /config get astakos.url',
                    'To set astakos url:   /config set astakos.url <URL>'])
            return r
        return _raise

    @classmethod
    def authenticate(this, foo):
        def _raise(self, *args, **kwargs):
            try:
                r = foo(self, *args, **kwargs)
            except ClientError as ce:
                if ce.status == 401:
                    token = kwargs.get('custom_token', 0) or self.client.token
                    raiseCLIError(ce,
                        'Authorization failed for token %s' % token if token\
                            else 'No token provided',
                        details=[] if token else this._token_details)
            self._raise = foo
            return r
        return _raise


class history(object):
    @classmethod
    def init(this, foo):
        @generic.all
        def _raise(self, *args, **kwargs):
            r = foo(self, *args, **kwargs)
            if not hasattr(self, 'history'):
                raise CLIError('Failed to load history', importance=2)
            return r
        return _raise

    @classmethod
    def _get_cmd_ids(this, foo):
        @generic.all
        def _raise(self, cmd_ids, *args, **kwargs):
            if not cmd_ids:
                raise CLISyntaxError('Usage: <id1|id1-id2> [id3|id3-id4] ...',
                    details=self.__doc__.split('\n'))
            return foo(self, cmd_ids, *args, **kwargs)
        return _raise

