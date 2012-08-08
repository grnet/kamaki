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

from kamaki.cli import command, set_api_description
from kamaki.utils import format_size
set_api_description('store', 'Pithos+ storage commands')
from .pithos import PithosClient, ClientError
from .cli_utils import raiseCLIError
from kamaki.utils import print_dict, pretty_keys, print_list
from colors import bold

from progress.bar import IncrementalBar


class ProgressBar(IncrementalBar):
    suffix = '%(percent)d%% - %(eta)ds'

class _pithos_init(object):
    def main(self):
        token = self.config.get('store', 'token') or self.config.get('global', 'token')
        base_url = self.config.get('store', 'url') or self.config.get('global', 'url')
        account = self.config.get('store', 'account') or self.config.get('global', 'account')
        container = self.config.get('store', 'container') or self.config.get('global', 'container')
        self.client = PithosClient(base_url=base_url, token=token, account=account, container=container)

class _store_account_command(_pithos_init):
    """Base class for account level storage commands"""

    def update_parser(self, parser):
        parser.add_argument('--account', dest='account', metavar='NAME',
                          help="Specify an account to use")

    def progress(self, message):
        """Return a generator function to be used for progress tracking"""

        MESSAGE_LENGTH = 25

        def progress_gen(n):
            msg = message.ljust(MESSAGE_LENGTH)
            for i in ProgressBar(msg).iter(range(n)):
                yield
            yield

        return progress_gen

    def main(self):
        super(_store_account_command, self).main()
        if self.args.account is not None:
            self.client.account = self.args.account

class _store_container_command(_store_account_command):
    """Base class for container level storage commands"""

    def update_parser(self, parser):
        super(_store_container_command, self).update_parser(parser)
        parser.add_argument('--container', dest='container', metavar='NAME',
                          help="Specify a container to use")

    def extract_container_and_path(self, container_with_path):
        assert isinstance(container_with_path, str)
        cnp = container_with_path.split(':')
        self.container = cnp[0]
        self.path = cnp[1] if len(cnp) > 1 else None
            

    def main(self, container_with_path=None):
        super(_store_container_command, self).main()
        if container_with_path is not None:
            self.extract_container_and_path(container_with_path)
            self.client.container = self.container
        elif self.args.container is not None:
            self.client.container = self.args.container
        else:
            self.container = None

@command()
class store_list(_store_container_command):
    """List containers, object trees or objects in a directory
    """

    def update_parser(self, parser):
        super(self.__class__, self).update_parser(parser)
        parser.add_argument('-l', action='store_true', dest='detail', default=False,
            help='show detailed output')
        """
        parser.add_argument('-n', action='store', dest='limit', default=10000,
            help='show limited output')
        parser.add_argument('--marker', action='store', dest='marker', default=None,
            help='show output greater then marker')
        parser.add_argument('--prefix', action='store', dest='prefix', default=None,
            help='show output starting with prefix')
        parser.add_argument('--delimiter', action='store', dest='delimiter', default=None, 
            help='show output up to the delimiter')
        parser.add_argument('--path', action='store', dest='path', default=None, 
            help='show output starting with prefix up to /')
        parser.add_argument('--meta', action='store', dest='meta', default=None, 
            help='show output having the specified meta keys')
        parser.add_argument('--if-modified-since', action='store', dest='if_modified_since', 
            default=None, help='show output if modified since then')
        parser.add_argument('--if-unmodified-since', action='store', dest='if_unmodified_since',
            default=None, help='show output if not modified since then')
        parser.add_argument('--until', action='store', dest='until', default=None,
            help='show metadata until that date')
        parser.add_argument('--format', action='store', dest='format', default='%d/%m/%Y %H:%M:%S',
            help='format to parse until date (default: %d/%m/%Y %H:%M:%S)')
        parser.add_argument('--shared', action='store_true', dest='shared', default=False,
            help='show only shared')
        parser.add_argument('--public', action='store_true', dest='public', default=False,
            help='show only public')
        """

    def print_objects(self, object_list):
        for obj in object_list:
            if obj['content_type'] == 'application/directory':
                size = ''
            else:
                size = format_size(obj['bytes'])
            oname = bold(obj['name'])
            if getattr(self.args, 'detail'):
                print(oname)
                print_dict(pretty_keys(obj), exclude=('name'), ident=18)
                print
            else:
                oname = '%6s %s'%(size, oname)
                oname += '/' if len(size) == 0 else ''
                print(oname)

    def print_containers(self, container_list):
        for container in container_list:
            size = format_size(container['bytes'])
            print('%s (%s, %s objects)' % (container['name'], size, container['count']))

    
    def main(self, container____path__=None):
        super(self.__class__, self).main(container____path__)
        try:
            if self.container is None:
                reply = self.client.list_containers()
                self.print_containers(reply)
            else:
                reply = self.client.list_objects() if self.path is None \
                    else self.client.list_objects_in_path(path_prefix=self.path)
                self.print_objects(reply)
        except ClientError as err:
            raiseCLIError(err)

@command()
class store_create(_store_container_command):
    """Create a container or a directory object"""

    def main(self, container____directory__):
        super(self.__class__, self).main(container____directory__)
        try:
            if self.path is None:
                self.client.create_container(self.container)
            else:
                self.client.create_directory(self.path)
        except ClientError as err:
            raiseCLIError(err)

@command()
class store_copy(_store_container_command):
    """Copy an object"""

    def main(self, source_container___path, destination_container____path__):
        super(self.__class__, self).main(source_container___path)
        try:
            dst = destination_container____path__.split(':')
            dst_cont = dst[0]
            dst_path = dst[1] if len(dst) > 1 else False
            self.client.copy_object(src_container = self.container, src_object = self.path,
                dst_container = dst_cont, dst_object = dst_path)
        except ClientError as err:
            raiseCLIError(err)

@command()
class store_move(_store_container_command):
    """Move an object"""

    def main(self, source_container___path, destination_container____path__):
        super(self.__class__, self).main(source_container___path)
        try:
            dst = destination_container____path__.split(':')
            dst_cont = dst[0]
            dst_path = dst[1] if len(dst) > 1 else False
            self.client.move_object(src_container = self.container, src_object = self.path,
                dst_container = dst_cont, dst_object = dst_path)
        except ClientError as err:
            raiseCLIError(err)

@command()
class store_append(_store_container_command):
    """Append local file to (existing) remote object"""

    
    def main(self, local_path, container___path):
        super(self.__class__, self).main(container___path)
        try:
            f = open(local_path, 'r')
            upload_cb = self.progress('Appending blocks')
            self.client.append_object(object=self.path, source_file = f, upload_cb = upload_cb)
        except ClientError as err:
            raiseCLIError(err)

@command()
class store_truncate(_store_container_command):
    """Truncate remote file up to a size"""

    
    def main(self, container___path, size=0):
        super(self.__class__, self).main(container___path)
        try:
            self.client.truncate_object(self.path, size)
        except ClientError as err:
            raiseCLIError(err)

@command()
class store_overwrite(_store_container_command):
    """Overwrite part (from start to end) of a remote file"""

    def main(self, local_path, container___path, start, end):
        super(self.__class__, self).main(container___path)
        try:
            f = open(local_path, 'r')
            upload_cb = self.progress('Overwritting blocks')
            self.client.overwrite_object(object=self.path, start=start, end=end,
                source_file=f, upload_cb = upload_cb)
        except ClientError as err:
            raiseCLIError(err)

@command()
class store_upload(_store_container_command):
    """Upload a file"""

    def main(self, local_path, container____path__):
        super(self.__class__, self).main(container____path__)
        try:
            remote_path = basename(local_path) if self.path is None else self.path
            with open(local_path) as f:
                hash_cb = self.progress('Calculating block hashes')
                upload_cb = self.progress('Uploading blocks')
                self.client.async_upload_object(remote_path, f, hash_cb=hash_cb, upload_cb=upload_cb)
        except ClientError as err:
            raiseCLIError(err)

@command()
class store_download(_store_container_command):
    """Download a file"""

    
    def main(self, container___path, local_path='-'):
        super(self.__class__, self).main(container___path)
        try:
            f, size = self.client.get_object(self.path)
        except ClientError as err:
            raiseCLIError(err)
        try:
            out = open(local_path, 'w') if local_path != '-' else stdout
        except IOError:
            raise CLIError(message='Cannot write to file %s'%local_path, importance=1)

        blocksize = 4 * 1024 ** 2
        nblocks = 1 + (size - 1) // blocksize

        cb = self.progress('Downloading blocks') if local_path != '-' else None
        if cb:
            gen = cb(nblocks)
            gen.next()

        data = f.read(blocksize)
        while data:
            out.write(data)
            data = f.read(blocksize)
            if cb:
                gen.next()

@command()
class store_delete(_store_container_command):
    """Delete a container [or an object]"""

    
    def main(self, container____path__):
        super(self.__class__, self).main(container____path__)
        try:
            if self.path is None:
                self.client.delete_container(self.container)
            else:
                self.client.delete_object(self.path)
        except ClientError as err:
            raiseCLIError(err)

@command()
class store_purge(_store_account_command):
    """Purge a container"""
    
    def main(self, container):
        super(self.__class__, self).main()
        try:
            self.client.container = container
            self.client.purge_container()
        except ClientError as err:
            raiseCLIError(err)

@command()
class store_publish(_store_container_command):
    """Publish an object"""

    def main(self, container___path):
        super(self.__class__, self).main(container___path)
        try:
            self.client.publish_object(self.path)
        except ClientError as err:
            raiseCLIError(err)

@command()
class store_unpublish(_store_container_command):
    """Unpublish an object"""

    def main(self, container___path):
        super(self.__class__, self).main(container___path)
        try:
            self.client.unpublish_object(self.path)
        except ClientError as err:
            raiseCLIError(err)

@command()
class store_permitions(_store_container_command):
    """Get object read/write permitions"""

    def main(self, container___path):
        super(self.__class__, self).main(container___path)
        try:
            reply = self.client.get_object_sharing(self.path)
            print_dict(reply)
        except ClientError as err:
            raiseCLIError(err)

@command()
class store_setpermitions(_store_container_command):
    """Set sharing permitions"""

    def main(self, container___path, *permitions):
        super(self.__class__, self).main(container___path)
        read = False
        write = False
        for perms in permitions:
            splstr = perms.split('=')
            if 'read' == splstr[0]:
                read = [user_or_group.strip() \
                for user_or_group in splstr[1].split(',')]
            elif 'write' == splstr[0]:
                write = [user_or_group.strip() \
                for user_or_group in splstr[1].split(',')]
            else:
                read = False
                write = False
        if not read and not write:
            raise CLIError(message='Usage:\tread=<groups,users> write=<groups,users>',
                importance=0)
        try:
            self.client.set_object_sharing(self.path,
                read_permition=read, write_permition=write)
        except ClientError as err:
            raiseCLIError(err)

@command()
class store_delpermitions(_store_container_command):
    """Delete all sharing permitions"""

    def main(self, container___path):
        super(self.__class__, self).main(container___path)
        try:
            self.client.del_object_sharing(self.path)
        except ClientError as err:
            raiseCLIError(err)

@command()
class store_info(_store_container_command):
    """Get information for account [, container [or object]]"""

    
    def main(self, container____path__=None):
        super(self.__class__, self).main(container____path__)
        try:
            if self.container is None:
                reply = self.client.get_account_info()
            elif self.path is None:
                reply = self.client.get_container_info(self.container)
            else:
                reply = self.client.get_object_info(self.path)
        except ClientError as err:
            raiseCLIError(err)
        print_dict(reply)

@command()
class store_meta(_store_container_command):
    """Get custom meta-content for account [, container [or object]]"""

    def main(self, container____path__ = None):
        super(self.__class__, self).main(container____path__)
        try:
            if self.container is None:
                reply = self.client.get_account_meta()
            elif self.path is None:
                reply = self.client.get_container_object_meta(self.container)
                print_dict(reply)
                reply = self.client.get_container_meta(self.container)
            else:
                reply = self.client.get_object_meta(self.path)
        except ClientError as err:
            raiseCLIError(err)
        print_dict(reply)

@command()
class store_setmeta(_store_container_command):
    """Set a new metadatum for account [, container [or object]]"""

    def main(self, metakey, metavalue, container____path__=None):
        super(self.__class__, self).main(container____path__)
        try:
            if self.container is None:
                self.client.set_account_meta({metakey:metavalue})
            elif self.path is None:
                self.client.set_container_meta({metakey:metavalue})
            else:
                self.client.set_object_meta(self.path, {metakey:metavalue})
        except ClientError as err:
            raiseCLIError(err)

@command()
class store_delmeta(_store_container_command):
    """Delete an existing metadatum of account [, container [or object]]"""

    def main(self, metakey, container____path__=None):
        super(self.__class__, self).main(container____path__)
        try:
            if self.container is None:
                self.client.del_account_meta(metakey)
            elif self.path is None:
                self.client.del_container_meta(metakey)
            else:
                self.client.del_object_meta(metakey, self.path)
        except ClientError as err:
            raiseCLIError(err)

@command()
class store_quota(_store_account_command):
    """Get  quota for account [or container]"""

    def main(self, container = None):
        super(self.__class__, self).main()
        try:
            if container is None:
                reply = self.client.get_account_quota()
            else:
                reply = self.client.get_container_quota(container)
        except ClientError as err:
            raiseCLIError(err)
        print_dict(reply)

@command()
class store_setquota(_store_account_command):
    """Set new quota (in KB) for account [or container]"""

    def main(self, quota, container = None):
        super(self.__class__, self).main()
        try:
            if container is None:
                self.client.set_account_quota(quota)
            else:
                self.client.container = container
                self.client.set_container_quota(quota)
        except ClientError as err:
            raiseCLIError(err)

@command()
class store_versioning(_store_account_command):
    """Get  versioning for account [or container ]"""

    def main(self, container = None):
        super(self.__class__, self).main()
        try:
            if container is None:
                reply = self.client.get_account_versioning()
            else:
                reply = self.client.get_container_versioning(container)
        except ClientError as err:
            raiseCLIError(err)
        print_dict(reply)

@command()
class store_setversioning(_store_account_command):
    """Set new versioning (auto, none) for account [or container]"""

    def main(self, versioning, container = None):
        super(self.__class__, self).main()
        try:
            if container is None:
                self.client.set_account_versioning(versioning)
            else:
                self.client.container = container
                self.client.set_container_versioning(versioning)
        except ClientError as err:
            raiseCLIError(err)

@command()
class store_group(_store_account_command):
    """Get user groups details for account"""

    def main(self):
        super(self.__class__, self).main()
        try:
            reply = self.client.get_account_group()
        except ClientError as err:
            raiseCLIError(err)
        print_dict(reply)

@command()
class store_setgroup(_store_account_command):
    """Create/update a new user group on account"""

    def main(self, groupname, *users):
        super(self.__class__, self).main()
        try:
            self.client.set_account_group(groupname, users)
        except ClientError as err:
            raiseCLIError(err)

@command()
class store_delgroup(_store_account_command):
    """Delete a user group on an account"""

    def main(self, groupname):
        super(self.__class__, self).main()
        try:
            self.client.del_account_group(groupname)
        except ClientError as err:
            raiseCLIError(err)
