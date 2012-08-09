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

from kamaki.cli import command, set_api_description, CLIError
from kamaki.clients.utils import filter_in
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
        self.client = PithosClient(base_url=base_url, token=token, account=account,
            container=container)

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
        if hasattr(self.args, 'account') and self.args.account is not None:
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
        elif hasattr(self.args, 'container') and self.args.container is not None:
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
        parser.add_argument('-N', action='store', dest='show_size', default=21,
            help='print output in chunks of size N')
        parser.add_argument('-n', action='store', dest='limit', default=None,
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
            help='show output having the specified meta keys (e.g. --meta "meta1 meta2 ..."')
        parser.add_argument('--if-modified-since', action='store', dest='if_modified_since', 
            default=None, help='show output if modified since then')
        parser.add_argument('--if-unmodified-since', action='store', dest='if_unmodified_since',
            default=None, help='show output if not modified since then')
        parser.add_argument('--until', action='store', dest='until', default=None,
            help='show metadata until that date')
        dateformat = '%d/%m/%Y %H:%M:%S'
        parser.add_argument('--format', action='store', dest='format', default=dateformat,
            help='format to parse until date (default: d/m/Y H:M:S)')
        parser.add_argument('--shared', action='store_true', dest='shared', default=False,
            help='show only shared')
        parser.add_argument('--public', action='store_true', dest='public', default=False,
            help='show only public')

    def print_objects(self, object_list):
        import sys
        try:
            limit = getattr(self.args, 'show_size')
            limit = int(limit)
        except AttributeError:
            pass
        index = 0
        for obj in object_list:
            if not obj.has_key('content_type'):
                continue
            pretty_obj = obj.copy()
            index += 1
            empty_space = ' '*(len(object_list)/10 - index/10)
            if obj['content_type'] == 'application/directory':
                isDir = True
                size = 'D'
            else:
                isDir = False
                size = format_size(obj['bytes'])
                pretty_obj['bytes'] = '%s (%s)'%(obj['bytes'],size)
            oname = bold(obj['name'])
            if getattr(self.args, 'detail'):
                print('%s%s. %s'%(empty_space, index, oname))
                print_dict(pretty_keys(pretty_obj), exclude=('name'))
                print
            else:
                oname = '%s%s. %6s %s'%(empty_space, index, size, oname)
                oname += '/' if isDir else ''
                print(oname)
            if limit <= index < len(object_list) and index%limit == 0:
                print('(press "enter" to continue)')
                sys.stdin.read(1)

    def print_containers(self, container_list):
        import sys
        try:
            limit = getattr(self.args, 'show_size')
            limit = int(limit)
        except AttributeError:
            pass
        for container in container_list:
            size = format_size(container['bytes'])
            index = 1+container_list.index(container)
            cname = '%s. %s'%(index, bold(container['name']))
            if getattr(self.args, 'detail'):
                print(cname)
                pretty_c = container.copy()
                pretty_c['bytes'] = '%s (%s)'%(container['bytes'], size)
                print_dict(pretty_keys(pretty_c), exclude=('name'))
                print
            else:
                print('%s (%s, %s objects)' % (cname, size, container['count']))
            if limit <= index < len(container_list) and index%limit == 0:
                print('(press "enter" to continue)')
                sys.stdin.read(1)

    def getuntil(self, orelse=None):
        if hasattr(self.args, 'until'):
            import time
            until = getattr(self.args, 'until')
            if until is None:
                return None
            format = getattr(self.args, 'format')
            #except TypeError:
            try:
                t = time.strptime(until, format)
            except ValueError as err:
                raise CLIError(message='in --until: '+unicode(err), importance=1)
            return int(time.mktime(t))
        return orelse
   
    def getmeta(self, orelse=[]):
        if hasattr(self.args, 'meta'):
            meta = getattr(self.args, 'meta')
            if meta is None:
                return []
            return meta.split(' ')
        return orelse

    def main(self, container____path__=None):
        super(self.__class__, self).main(container____path__)
        try:
            if self.container is None:
                r = self.client.account_get(limit=getattr(self.args, 'limit', None),
                    marker=getattr(self.args, 'marker', None),
                    if_modified_since=getattr(self.args, 'if_modified_since', None),
                    if_unmodified_since=getattr(self.args, 'if_unmodified_since', None),
                    until=self.getuntil(),
                    show_only_shared=getattr(self.args, 'shared', False))
                self.print_containers(r.json)
            else:
                r = self.client.container_get(limit=getattr(self.args, 'limit', None),
                    marker=getattr(self.args, 'marker', None),
                    prefix=getattr(self.args, 'prefix', None),
                    delimiter=getattr(self.args, 'delimiter', None),
                    path=getattr(self.args, 'path', None) if self.path is None else self.path,
                    if_modified_since=getattr(self.args, 'if_modified_since', None),
                    if_unmodified_since=getattr(self.args, 'if_unmodified_since', None),
                    until=self.getuntil(),
                    meta=self.getmeta(),
                    show_only_shared=getattr(self.args, 'shared', False))
                self.print_objects(r.json)
        except ClientError as err:
            raiseCLIError(err)

@command()
class store_mkdir(_store_container_command):
    """Create a directory"""

    def main(self, directory):
        super(self.__class__, self).main()
        try:
            self.client.create_directory(directory)
        except ClientError as err:
            raiseCLIError(err)

@command()
class store_create(_store_container_command):
    """Create a container or a directory object"""

    def update_parser(self, parser):
        parser.add_argument('--versioning', action='store', dest='versioning',
                          default=None, help='set container versioning (auto/none)')
        parser.add_argument('--quota', action='store', dest='quota',
                          default=None, help='set default container quota')

    def main(self, container____directory__):
        super(self.__class__, self).main(container____directory__)
        try:
            if self.path is None:
                self.client.container_put(quota=getattr(self.args, 'quota'),
                    versioning=getattr(self.args, 'versioning'))
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

    def update_parser(self, parser):
        parser.add_argument('-l', action='store_true', dest='detail', default=False,
            help='show detailed output')
        parser.add_argument('--until', action='store', dest='until', default=None,
            help='show metadata until that date')
        dateformat='%d/%m/%Y %H:%M:%S'
        parser.add_argument('--format', action='store', dest='format', default=dateformat,
            help='format to parse until date (default: "d/m/Y H:M:S")')
        parser.add_argument('--object_version', action='store', dest='object_version', default=None,
            help='show specific version \ (applies only for objects)')

    def getuntil(self, orelse=None):
        if hasattr(self.args, 'until'):
            import time
            until = getattr(self.args, 'until')
            if until is None:
                return None
            format = getattr(self.args, 'format')
            #except TypeError:
            try:
                t = time.strptime(until, format)
            except ValueError as err:
                raise CLIError(message='in --until: '+unicode(err), importance=1)
            return int(time.mktime(t))
        return orelse

    def main(self, container____path__ = None):
        super(self.__class__, self).main(container____path__)

        try:
            if self.container is None:
                print(bold(self.client.account))
                r = self.client.account_head(until=self.getuntil())
                reply = r.headers if getattr(self.args, 'detail') \
                    else pretty_keys(filter_in(r.headers, 'X-Account-Meta'), '-')
            elif self.path is None:
                print(bold(self.client.account+': '+self.container))
                r = self.client.container_head(until=self.getuntil())
                if getattr(self.args, 'detail'):
                    reply = r.headers
                else:
                    cmeta = 'container-meta'
                    ometa = 'object-meta'
                    reply = {cmeta:pretty_keys(filter_in(r.headers, 'X-Container-Meta'), '-'),
                        ometa:pretty_keys(filter_in(r.headers, 'X-Container-Object-Meta'), '-')}
            else:
                print(bold(self.client.account+': '+self.container+':'+self.path))
                r = self.client.object_head(self.path, version=getattr(self.args, 'object_version'))
                reply = r.headers if getattr(self.args, 'detail') \
                    else pretty_keys(filter_in(r.headers, 'X-Object-Meta'), '-')
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
