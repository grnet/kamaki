# Copyright 2014-2015 GRNET S.A. All rights reserved.
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

from kamaki.cli import command
from kamaki.cli.errors import CLIInvalidArgument
from kamaki.cli.cmdtree import CommandTree
from kamaki.cli.cmds import (
    CommandInit, errors, client_log, OptionalOutput, Wait)
from kamaki.clients.cyclades import CycladesBlockStorageClient, ClientError
from kamaki.cli import argument


volume_cmds = CommandTree('volume', 'Block Storage API volume commands')
snapshot_cmds = CommandTree('snapshot', 'Block Storage API snapshot commands')
namespaces = [volume_cmds, snapshot_cmds]
_commands = namespaces

volume_states = (
    'creating',  'available', 'attaching', 'detaching', 'in_use', 'deleting',
    'deleted', 'error', 'error_deleting', 'backing_up', 'restoring_backup',
    'error_restoring', )


class _VolumeWait(Wait):

    def wait_while(self, volume_id, current_status, timeout=60):
        super(_VolumeWait, self).wait(
            'Volume', volume_id, self.client.wait_volume_while, current_status,
            timeout=timeout)

    def wait_until(self, volume_id, target_status, timeout=60):
        super(_VolumeWait, self).wait(
            'Volume', volume_id, self.client.wait_volume_until, target_status,
            timeout=timeout, msg='not yet')


class _BlockStorageInit(CommandInit):
    @errors.Generic.all
    @client_log
    def _run(self):
        self.client = self.get_client(CycladesBlockStorageClient, 'volume')

    def main(self):
        self._run()


@command(volume_cmds)
class volume_list(_BlockStorageInit, OptionalOutput):
    """List volumes"""

    arguments = dict(
        detail=argument.FlagArgument(
            'show detailed output', ('-l', '--details')),
    )

    @errors.Generic.all
    def _run(self):
        self.print_(self.client.list_volumes(detail=self['detail']))

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(volume_cmds)
class volume_info(_BlockStorageInit, OptionalOutput):
    """Get details about a volume"""

    @errors.Generic.all
    def _run(self, volume_id):
        self.print_(
            self.client.get_volume_details(volume_id), self.print_dict)

    def main(self, volume_id):
        super(self.__class__, self)._run()
        self._run(volume_id=volume_id)


@command(volume_cmds)
class volume_create(_BlockStorageInit, OptionalOutput, _VolumeWait):
    """Create a new volume"""

    arguments = dict(
        size=argument.IntArgument('Volume size in GB', '--size'),
        server_id=argument.ValueArgument(
            'The server to attach the volume to', '--server-id'),
        name=argument.ValueArgument('Display name', '--name'),
        description=argument.ValueArgument(
            'Volume description', '--description'),
        snapshot_id=argument.ValueArgument(
            'Associate a snapshot to the new volume', '--snapshot-id'),
        image_id=argument.ValueArgument(
            'Associate an image to the new volume', '--image-id'),
        volume_type=argument.ValueArgument(
            'default: if combined with --server-id, the default is '
            'automatically configured to match the server, otherwise it is '
            'ext_archipelago',
            '--volume-type'),
        metadata=argument.KeyValueArgument(
            'Metadata of key=value form (can be repeated)', '--metadata'),
        project_id=argument.ValueArgument(
            'Assign volume to a project', '--project-id'),
        wait=argument.FlagArgument(
            'Wait volume to be created and ready for use', ('-w', '--wait')),
    )
    required = ('size', 'name')

    @errors.Generic.all
    def _run(self, size, name):
        # Figure out volume type
        volume_type = self['volume_type']
        if not (self['server_id'] or volume_type):
            for vtype in self.client.list_volume_types():
                if vtype['name'] in ('ext_archipelago'):
                    volume_type = vtype['id']
                    break

        r = self.client.create_volume(
            size, name,
            server_id=self['server_id'],
            display_description=self['description'],
            snapshot_id=self['snapshot_id'],
            imageRef=self['image_id'],
            volume_type=volume_type,
            metadata=self['metadata'],
            project=self['project_id'])
        self.print_dict(r)
        r = self.client.get_volume_details(r['id'])
        if self['wait'] and r['status'] != 'in_use':
            self.wait_while(r['id'], r['status'])
            r = self.client.get_volume_details(r['id'])
            if r['status'] != 'in_use':
                exit(1)

    def main(self):
        super(self.__class__, self)._run()
        self._run(
            size=self['size'], name=self['name'])


@command(volume_cmds)
class volume_modify(_BlockStorageInit, OptionalOutput):
    """Modify a volume's properties"""

    arguments = dict(
        name=argument.ValueArgument('Rename', '--name'),
        description=argument.ValueArgument('New description', '--description'),
        delete_on_termination=argument.BooleanArgument(
            'Delete on termination', '--delete-on-termination'))
    required = ['name', 'description', 'delete_on_termination']

    @errors.Generic.all
    def _run(self, volume_id):
        self.print_(
            self.client.update_volume(
                volume_id,
                display_name=self['name'],
                display_description=self['description'],
                delete_on_termination=self['delete_on_termination']),
            self.print_dict)

    def main(self, volume_id):
        super(self.__class__, self)._run()
        self._run(volume_id)


@command(volume_cmds)
class volume_reassign(_BlockStorageInit):
    """Reassign volume to a different project"""

    arguments = dict(
        project_id=argument.ValueArgument('Project to assign', '--project-id'),
    )
    required = ('project_id', )

    @errors.Generic.all
    def _run(self, volume_id, project_id):
        self.client.reassign_volume(volume_id, project_id)

    def main(self, volume_id):
        super(self.__class__, self)._run()
        self._run(volume_id=volume_id, project_id=self['project_id'])


@command(volume_cmds)
class volume_delete(_BlockStorageInit, _VolumeWait):
    """Delete a volume"""

    arguments = dict(
        wait=argument.FlagArgument('Wait until deleted', ('-w', '--wait')),
    )

    @errors.Generic.all
    def _run(self, volume_id):
        r = self.client.get_volume_details(volume_id)
        self.client.delete_volume(volume_id)
        if self['wait']:
            try:
                self.wait_while(volume_id, r['status'])
                r = self.client.get_volume_details(volume_id)
                if r['status'] != 'deleted':
                    exit(1)
            except ClientError as ce:
                if ce.status not in (404, ):
                    raise

    def main(self, volume_id):
        super(self.__class__, self)._run()
        self._run(volume_id=volume_id)


@command(volume_cmds)
class volume_wait(_BlockStorageInit, _VolumeWait):
    """Wait for volume to finish (default: --while creating)"""

    arguments = dict(
        timeout=argument.IntArgument(
            'Wait limit in seconds (default: 60)', '--timeout', default=60),
        status_w=argument.StatusArgument(
            'Wait while in status (%s)' % ','.join(volume_states), '--while',
            valid_states=volume_states),
        status_u=argument.StatusArgument(
            'Wait until status is reached (%s)' % ','.join(volume_states),
            '--until',
            valid_states=volume_states),
    )

    @errors.Generic.all
    def _run(self, volume_id):
        r = self.client.get_volume_details(volume_id)
        if self['status_u']:
            if r['status'] == self['status_u'].lower():
                self.error('Volume %s: already in %s' % (
                    volume_id, r['status']))
            else:
                self.wait_until(
                    volume_id, self['status_u'].lower(),
                    timeout=self['timeout'])
        else:
            status_w = (self['status_w'] or '').lower() or 'creating'
            if r['status'] == status_w.lower():
                self.wait_while(volume_id, status_w, timeout=self['timeout'])
            else:
                self.error('Volume %s status: %s' % (volume_id, r['status']))

    def main(self, volume_id):
        super(self.__class__, self)._run()
        if all([self['status_w'], self['status_u']]):
            raise CLIInvalidArgument(
                'Invalid argument combination', importance=2, details=[
                    'Arguments %s and %s are mutually exclusive' % (
                        self.arguments['status_w'].lvalue,
                        self.arguments['status_u'].lvalue)])
        self._run(volume_id=volume_id)


@command(volume_cmds)
class volume_types(_BlockStorageInit, OptionalOutput):
    """List volume types"""

    @errors.Generic.all
    def _run(self):
        self.print_(self.client.list_volume_types())

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(volume_cmds)
class volume_type(_BlockStorageInit, OptionalOutput):
    """Get volume type details"""

    @errors.Generic.all
    def _run(self, volume_type_id):
        self.print_(
            self.client.get_volume_type_details(volume_type_id),
            self.print_dict)

    def main(self, volume_type_id):
        super(self.__class__, self)._run()
        self._run(volume_type_id=volume_type_id)


@command(snapshot_cmds)
class snapshot_list(_BlockStorageInit, OptionalOutput):
    """List snapshots"""

    arguments = dict(
        detail=argument.FlagArgument(
            'show detailed output', ('-l', '--details')),
    )

    @errors.Generic.all
    def _run(self):
        self.print_(self.client.list_snapshots(detail=self['detail']))

    def main(self):
        super(self.__class__, self)._run()
        self._run()


@command(snapshot_cmds)
class snapshot_info(_BlockStorageInit, OptionalOutput):
    """Get details about a snapshot"""

    @errors.Generic.all
    def _run(self, snapshot_id):
        self.print_(
            self.client.get_snapshot_details(snapshot_id), self.print_dict)

    def main(self, snapshot_id):
        super(self.__class__, self)._run()
        self._run(snapshot_id=snapshot_id)


@command(snapshot_cmds)
class snapshot_create(_BlockStorageInit, OptionalOutput):
    """Create a new snapshot"""

    arguments = dict(
        volume_id=argument.ValueArgument(
            'Volume associated to new snapshot', '--volume-id'),
        name=argument.ValueArgument('Display name', '--name'),
        description=argument.ValueArgument('New description', '--description'),
    )
    required = ('volume_id', )

    @errors.Generic.all
    def _run(self, volume_id):
        self.print_(
            self.client.create_snapshot(
                volume_id,
                display_name=self['name'],
                display_description=self['description']),
            self.print_dict)

    def main(self):
        super(self.__class__, self)._run()
        self._run(volume_id=self['volume_id'])


@command(snapshot_cmds)
class snapshot_modify(_BlockStorageInit, OptionalOutput):
    """Modify a snapshot's properties"""

    arguments = dict(
        name=argument.ValueArgument('Rename', '--name'),
        description=argument.ValueArgument('New description', '--description'),
    )
    required = ['name', 'description']

    @errors.Generic.all
    def _run(self, snapshot_id):
        self.print_(
            self.client.update_snapshot(
                snapshot_id,
                display_name=self['name'],
                display_description=self['description']),
            self.print_dict)

    def main(self, snapshot_id):
        super(self.__class__, self)._run()
        self._run(snapshot_id=snapshot_id)


@command(snapshot_cmds)
class snapshot_delete(_BlockStorageInit):
    """Delete a snapshot"""

    @errors.Generic.all
    def _run(self, snapshot_id):
        self.client.delete_snapshot(snapshot_id)

    def main(self, snapshot_id):
        super(self.__class__, self)._run()
        self._run(snapshot_id=snapshot_id)
