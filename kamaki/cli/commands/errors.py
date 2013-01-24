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

    @classmethod
    def _connection(this, foo, base_url):
        def _raise(self, *args, **kwargs):
            try:
                foo(self, *args, **kwargs)
            except ClientError as ce:
                if ce.status == 401:
                    raiseCLIError(ce, 'Authorization failed', details=[
                        'Make sure a valid token is provided:',
                        '  to check if token is valid: /astakos authenticate',
                        '  to set token: /config set [.server.]token <token>',
                        '  to get current token: /config get [server.]token'])
                elif ce.status in range(-12, 200) + [302, 401, 403, 500]:
                    raiseCLIError(ce, importance=3, details=[
                        'Check if service is up or set to url %s' % base_url,
                        '  to get url: /config get %s' % base_url,
                        '  to set url: /config set %s <URL>' % base_url])
                elif ce.status == 404\
                and 'kamakihttpresponse' in ('%s' % ce).lower():
                    client = getattr(self, 'client', None)
                    if not client:
                        raise
                    url = getattr(client, 'base_url', '<empty>')
                    raiseCLIError(ce,
                        'Invalid service url %s' % url,
                        details=[
                        'Please, check if service url is correctly set',
                        '* to get current url: /config get compute.url',
                        '* to set url: /config set compute.url <URL>'])
                raise
        return _raise


class astakos(object):

    _token_details = [
        'To check default token: /config get token',
        'If set/update a token:',
        '*  (permanent):    /config set token <token>',
        '*  (temporary):    re-run with <token> parameter']

    @classmethod
    def load(this, foo):
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
        def _raise(self, *args, **kwargs):
            r = foo(self, *args, **kwargs)
            if not hasattr(self, 'history'):
                raise CLIError('Failed to load history', importance=2)
            return r
        return _raise

    @classmethod
    def _get_cmd_ids(this, foo):
        def _raise(self, cmd_ids, *args, **kwargs):
            if not cmd_ids:
                raise CLISyntaxError('Usage: <id1|id1-id2> [id3|id3-id4] ...',
                    details=self.__doc__.split('\n'))
            return foo(self, cmd_ids, *args, **kwargs)
        return _raise


class cyclades(object):
    about_flavor_id = [
        'How to pick a valid flavor id:',
        '* get a list of flavor ids: /flavor list',
        '* details of flavor: /flavor info <flavor id>']

    about_network_id = [
        'How to pick a valid network id:',
        '* get a list of network ids: /network list',
        '* details of network: /network info <network id>']

    @classmethod
    def connection(this, foo):
        return generic._connection(foo, 'compute.url')

    @classmethod
    def date(this, foo):
        def _raise(self, *args, **kwargs):
            try:
                return foo(self, *args, **kwargs)
            except ClientError as ce:
                if ce.status == 400 and 'changes-since' in ('%s' % ce):
                    raise CLIError(
                        'Incorrect date format for --since',
                        details=['Accepted date format: d/m/y'])
                raise
        return _raise

    @classmethod
    def network_id(this, foo):
        def _raise(self, *args, **kwargs):
            network_id = kwargs.get('network_id', None)
            try:
                network_id = int(network_id)
                return foo(self, *args, **kwargs)
            except ValueError as ve:
                raiseCLIError(ve, 'Invalid network id %s ' % network_id,
                    details='network id must be a positive integer',
                    importance=1)
            except ClientError as ce:
                if network_id and ce.status == 404 and\
                    'network' in ('%s' % ce).lower():
                        raiseCLIError(ce,
                            'No network with id %s found' % network_id,
                            details=this.about_network_id)
                raise
        return _raise

    @classmethod
    def network_max(this, foo):
        def _raise(self, *args, **kwargs):
            try:
                return foo(self, *args, **kwargs)
            except ClientError as ce:
                if ce.status == 413:
                    raiseCLIError(ce,
                        'Cannot create another network',
                        details=['Maximum number of networks reached',
                            '* to get a list of networks: /network list',
                            '* to delete a network: /network delete <net id>'])
                raise
        return _raise

    @classmethod
    def network_in_use(this, foo):
        def _raise(self, *args, **kwargs):
            network_id = kwargs.get('network_id', None)
            try:
                return foo(self, *args, **kwargs)
            except ClientError as ce:
                if network_id or ce.status == 421:
                    raiseCLIError(ce,
                        'Network with id %s is in use' % network_id,
                        details=[
                            'Disconnect all nics/VMs of this network first',
                            '* to get nics: /network info %s' % network_id,
                            '.  (under "attachments" section)',
                            '* to disconnect: /network disconnect <nic id>'])
                raise
        return _raise

    @classmethod
    def flavor_id(this, foo):
        def _raise(self, *args, **kwargs):
            flavor_id = kwargs.get('flavor_id', None)
            try:
                flavor_id = int(flavor_id)
                return foo(self, *args, **kwargs)
            except ValueError as ve:
                raiseCLIError(ve, 'Invalid flavor id %s ' % flavor_id,
                    details='Flavor id must be a positive integer',
                    importance=1)
            except ClientError as ce:
                if flavor_id and ce.status == 404 and\
                    'flavor' in ('%s' % ce).lower():
                        raiseCLIError(ce,
                            'No flavor with id %s found' % flavor_id,
                            details=this.about_flavor_id)
                raise
        return _raise

    @classmethod
    def server_id(this, foo):
        def _raise(self, *args, **kwargs):
            server_id = kwargs.get('server_id', None)
            try:
                server_id = int(server_id)
                return foo(self, *args, **kwargs)
            except ValueError as ve:
                raiseCLIError(ve,
                    'Invalid server(VM) id %s' % server_id,
                    details=['id must be a positive integer'],
                    importance=1)
            except ClientError as ce:
                err_msg = ('%s' % ce).lower()
                if (ce.status == 404 and 'server' in err_msg)\
                or (ce.status == 400 and 'not found' in err_msg):
                    raiseCLIError(ce,
                        'server(VM) with id %s not found' % server_id,
                        details=[
                            '* to get existing VM ids: /server list',
                            '* to get VM details: /server info <VM id>'])
                raise
        return _raise

    @classmethod
    def firewall(this, foo):
        def _raise(self, *args, **kwargs):
            profile = kwargs.get('profile', None)
            try:
                return foo(self, *args, **kwargs)
            except ClientError as ce:
                if ce.status == 400 and profile\
                and 'firewall' in ('%s' % ce).lower():
                    raiseCLIError(ce,
                        '%s is an invalid firewall profile term' % profile,
                        details=['Try one of the following:',
                            '* DISABLED: Shutdown firewall',
                            '* ENABLED: Firewall in normal mode',
                            '* PROTECTED: Firewall in secure mode'])
                raise
        return _raise

    @classmethod
    def nic_id(this, foo):
        def _raise(self, *args, **kwargs):
            try:
                return foo(self, *args, **kwargs)
            except ClientError as ce:
                nic_id = kwargs.get('nic_id', None)
                if nic_id and ce.status == 404\
                and 'network interface' in ('%s' % ce).lower():
                    server_id = kwargs.get('server_id', '<no server>')
                    err_msg = 'No nic %s on server(VM) with id %s' % (
                        nic_id,
                        server_id)
                    raiseCLIError(ce, err_msg, details=[
                        '* check server(VM) with id %s: /server info %s' % (
                            server_id,
                            server_id),
                        '* list nics for server(VM) with id %s:' % server_id,
                        '      /server addr %s' % server_id])
                raise
        return _raise

    @classmethod
    def nic_format(this, foo):
        def _raise(self, *args, **kwargs):
            try:
                return foo(self, *args, **kwargs)
            except IndexError as ie:
                nic_id = kwargs.get('nic_id', None)
                raiseCLIError(ie,
                    'Invalid format for network interface (nic) %s' % nic_id,
                    importance=1,
                    details=[
                        'nid_id format: nic-<server id>-<nic id>',
                        '* get nics of a network: /network info <net id>',
                        '    (listed the "attachments" section)'])
        return _raise

    @classmethod
    def metadata(this, foo):
        def _raise(self, *args, **kwargs):
            key = kwargs.get('key', None)
            try:
                foo(self, *args, **kwargs)
            except ClientError as ce:
                if key and ce.status == 404\
                    and 'metadata' in ('%s' % ce).lower():
                        raiseCLIError(ce, 'No VM metadata with key %s' % key)
                raise
        return _raise


class plankton(object):

    about_image_id = ['How to pick a suitable image:',
        '* get a list of image ids: /image list',
        '* details of image: /flavor info <image id>']

    @classmethod
    def connection(this, foo):
        return generic._connection(foo, 'image.url')

    @classmethod
    def id(this, foo):
        def _raise(self, *args, **kwargs):
            image_id = kwargs.get('image_id', None)
            try:
                foo(self, *args, **kwargs)
            except ClientError as ce:
                if image_id and (ce.status == 404\
                    or (ce.status == 400 and
                        'image not found' in ('%s' % ce).lower())\
                    or ce.status == 411):
                        raiseCLIError(ce,
                            'No image with id %s found' % image_id,
                            details=this.about_image_id)
                raise
        return _raise

    @classmethod
    def metadata(this, foo):
        def _raise(self, *args, **kwargs):
            key = kwargs.get('key', None)
            try:
                foo(self, *args, **kwargs)
            except ClientError as ce:
                if ce.status == 404 or ((ce.status == 400\
                    and 'metadata' in ('%s' % ce).lower())):
                        raiseCLIError(ce,
                            'No properties with key %s in this image' % key)
                raise
        return _raise


class pithos(object):
    container_howto = ['To specify a container:',
    '  1. Set store.container variable (permanent)',
    '     /config set store.container <container>',
    '  2. --container=<container> (temporary, overrides 1)',
    '  3. Use the container:path format (temporary, overrides all)']

    @classmethod
    def connection(this, foo):
        return generic._connection(foo, 'store.url')

    @classmethod
    def quota(this, foo):
        def _raise(self, *args, **kwargs):
            try:
                return foo(self, *args, **kwargs)
            except ClientError as ce:
                if ce.status == 413:
                    raiseCLIError(ce, 'User quota exceeded', details=[
                        '* get quotas:',
                        '  * upper total limit:      /store quota',
                        '  * container limit:  /store quota <container>',
                        '* set a higher quota (if permitted):',
                        '    /store setquota <quota>[unit] <container>'
                        '    as long as <container quota> <= <total quota>'])
                raise
        return _raise

    @classmethod
    def container(this, foo):
        def _raise(self, *args, **kwargs):
            dst_cont = kwargs.get('dst_cont', None)
            try:
                return foo(self, *args, **kwargs)
            except ClientError as ce:
                if ce.status == 404 and 'container' in ('%s' % ce).lower():
                        cont = '%s or %s' if dst_cont else self.container
                        raiseCLIError(ce,
                            'No container %s in account %s' % (
                                cont,
                                self.account),
                            details=this.container_howto)
                raise
        return _raise

    @classmethod
    def object_path(this, foo):
        def _raise(self, *args, **kwargs):
            try:
                return foo(self, *args, **kwargs)
            except ClientError as ce:
                err_msg = ('%s' % ce).lower()
                if ce.status == 404 and 'object not found' in err_msg:
                    raiseCLIError(ce,
                        'No object %s in %s\'s container %s'\
                        % (self.path, self.account, self.container),
                        details=this.container_howto)
                raise
        return _raise
