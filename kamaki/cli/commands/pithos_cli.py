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

from kamaki.cli import command#, set_api_description
from kamaki.clients.utils import filter_in
from kamaki.cli.errors import CLIError, raiseCLIError
from kamaki.cli.utils import format_size, print_dict, pretty_keys, print_list
from kamaki.cli.argument import FlagArgument, ValueArgument
#set_api_description('store', 'Pithos+ storage commands')
API_DESCRIPTION = {'store':'Pithos+ storage commands'}
from kamaki.clients.pithos import PithosClient, ClientError
from colors import bold
from sys import stdout, exit
import signal
from time import localtime, strftime, strptime, mktime

from progress.bar import IncrementalBar

class UntilArgument(ValueArgument):
    @property 
    def value(self):
        if self._value is None:
            return self.default
        format = self.get_argument('format')
        try:
            t = time.strptime(until, format)
        except ValueError as err:
            raise CLIError(message='in --until: '+unicode(err), importance=1)
        return int(mktime(t))

class MetaArgument(ValueArgument):
    @property 
    def value(self):
        if self._value is None:
            return self.default
        metadict = dict()
        for metastr in self._value.split('_'):
            (key,val) = metastr.split(':')
            metadict[key]=val
        return metadict

class ProgressBar(IncrementalBar):
    #suffix = '%(percent)d%% - %(eta)ds'
    suffix = '%(percent)d%%'

class _pithos_init(object):
    def __init__(self, arguments={}):
        self.arguments = arguments
        try:
            self.config = self.get_argument('config')
        except KeyError:
            pass

    def get_argument(self, arg_name):
        return self.arguments[arg_name].value

    def main(self):
        self.token = self.config.get('store', 'token') or self.config.get('global', 'token')
        self.base_url = self.config.get('store', 'url') or self.config.get('global', 'url')
        self.account = self.config.get('store', 'account') or self.config.get('global', 'account')
        self.container = self.config.get('store', 'container') or self.config.get('global',
            'container')
        self.client = PithosClient(base_url=self.base_url, token=self.token, account=self.account,
            container=self.container)

class _store_account_command(_pithos_init):
    """Base class for account level storage commands"""

    def __init__(self, arguments={}):
        super(_store_account_command, self).__init__(arguments)
        self.arguments['account'] = ValueArgument('Specify the account', '--account')

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
        if self.arguments['account'].value is not None:
            self.client.account = self.arguments['account'].value

class _store_container_command(_store_account_command):
    """Base class for container level storage commands"""

    def __init__(self, arguments={}):
        super(_store_container_command, self).__init__(arguments)
        self.arguments['container'] = ValueArgument('Specify the container name', '--container')
        self.container = None
        self.path = None

    def extract_container_and_path(self, container_with_path, path_is_optional=True):
        assert isinstance(container_with_path, str)
        if ':' not in container_with_path:
            if self.get_argument('container') is not None:
                self.container = self.get_argument('container')
            else:
                self.container = self.client.container
            if self.container is None:
                self.container = container_with_path
            else:
                self.path = container_with_path
            if not path_is_optional and self.path is None:
                raise CLIError(message="Object path is missing", status=11)
            return
        cnp = container_with_path.split(':')
        self.container = cnp[0]
        try:
            self.path = cnp[1]
        except IndexError:
            if path_is_optional:
                self.path = None
            else:
                raise CLIError(message="Object path is missing", status=11)

    def main(self, container_with_path=None, path_is_optional=True):
        super(_store_container_command, self).main()
        if container_with_path is not None:
            self.extract_container_and_path(container_with_path, path_is_optional)
            self.client.container = self.container
        elif self.get_argument('container') is not None:
            self.client.container = self.get_argument('container')
        self.container = self.client.container

"""
@command()
class store_test(_store_container_command):
    "Test stuff something""

    def main(self):
        super(self.__class__, self).main('pithos')
        r = self.client.container_get()
        print(unicode(r.content)+' '+unicode(r.json))
"""

@command()
class store_list(_store_container_command):
    """List containers, object trees or objects in a directory
    """


    def __init__(self, arguments = {}):
        super(store_list, self).__init__(arguments)
        self.arguments['detail'] = FlagArgument('show detailed output', '-l')
        self.arguments['show_size'] = ValueArgument('print output in chunks of size N', '-N')
        self.arguments['limit'] = ValueArgument('show limited output', '-n')
        self.arguments['marker'] = ValueArgument('show output greater that marker', '--marker')
        self.arguments['prefix'] = ValueArgument('show output staritng with prefix', '--prefix')
        self.arguments['delimiter'] = ValueArgument('show output up to delimiter', '--delimiter')
        self.arguments['path'] = ValueArgument('show output starting with prefix up to /', '--path')
        self.arguments['meta'] = ValueArgument('show output haviung the specified meta keys',
            '---meta', default=[])
        self.arguments['if_modified_since'] = ValueArgument('show output modified since then',
            '--if-modified-since')
        self.arguments['if_unmodified_since'] = ValueArgument('show output not modified since then',
            '--if-unmodified-since')
        self.arguments['until'] = UntilArgument('show metadata until then', '--until')
        self.arguments['format'] = ValueArgument('format to parse until data (default: d/m/Y H:M:S',
            '--format')
        self.arguments['shared'] = FlagArgument('show only shared', '--shared')
        self.arguments['public'] = FlagArgument('show only public', '--public')

    def print_objects(self, object_list):
        import sys
        try:
            limit = self.get_argument('show_size')
            limit = int(limit)
        except AttributeError:
            pass
        #index = 0
        for index,obj in enumerate(object_list):
            if not obj.has_key('content_type'):
                continue
            pretty_obj = obj.copy()
            index += 1
            empty_space = ' '*(len(str(len(object_list))) - len(str(index)))
            if obj['content_type'] == 'application/directory':
                isDir = True
                size = 'D'
            else:
                isDir = False
                size = format_size(obj['bytes'])
                pretty_obj['bytes'] = '%s (%s)'%(obj['bytes'],size)
            oname = bold(obj['name'])
            if self.get_argument('detail'):
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
            limit = self.get_argument('show_size')
            limit = int(limit)
        except AttributeError:
            pass
        for index,container in enumerate(container_list):
            if container.has_key('bytes'):
                size = format_size(container['bytes']) 
            cname = '%s. %s'%(index+1, bold(container['name']))
            if self.get_argument('detail'):
                print(cname)
                pretty_c = container.copy()
                if container.has_key('bytes'):
                    pretty_c['bytes'] = '%s (%s)'%(container['bytes'], size)
                print_dict(pretty_keys(pretty_c), exclude=('name'))
                print
            else:
                if container.has_key('count') and container.has_key('bytes'):
                    print('%s (%s, %s objects)' % (cname, size, container['count']))
                else:
                    print(cname)
            if limit <= index < len(container_list) and index%limit == 0:
                print('(press "enter" to continue)')
                sys.stdin.read(1)


    def main(self, container____path__=None):
        super(self.__class__, self).main(container____path__)
        try:
            if self.container is None:
                r = self.client.account_get(limit=self.get_argument('limit'),
                    marker=self.get_argument('marker'),
                    if_modified_since=self.get_argument('if_modified_since'),
                    if_unmodified_since=self.get_argument('if_unmodified_since'),
                    until=self.get_argument('until'),
                    show_only_shared=self.get_argument('shared'))
                self.print_containers(r.json)
            else:
                r = self.client.container_get(limit=self.get_argument('limit'),
                    marker=self.get_argument('marker'), prefix=self.get_argument('prefix'),
                    delimiter=self.get_argument('delimiter'), path=self.get_argument('path'),
                    if_modified_since=self.get_argument('if_modified_since'),
                    if_unmodified_since=self.get_argument('if_unmodified_since'),
                    until=self.get_argument('until'),
                    meta=self.get_argument('meta'), show_only_shared=self.get_argument('shared'))
                self.print_objects(r.json)
        except ClientError as err:
            raiseCLIError(err)

@command()
class store_mkdir(_store_container_command):
    """Create a directory"""

    def main(self, container___directory):
        super(self.__class__, self).main(container___directory, path_is_optional=False)
        try:
            self.client.create_directory(self.path)
        except ClientError as err:
            raiseCLIError(err)

@command()
class store_create(_store_container_command):
    """Create a container or a directory object"""


    def __init__(self, arguments={}):
        super(self.__class__, self).__init__(arguments)
        self.arguments['versioning'] = ValueArgument('set container versioning (auto/none)',
            '--versioning')
        self.arguments['quota'] = ValueArgument('set default container quota', '--quota')
        self.arguments['meta'] = MetaArgument('set container metadata', '---meta')

    def main(self, container____directory__):
        super(self.__class__, self).main(container____directory__)
        try:
            if self.path is None:
                self.client.container_put(quota=self.get_argument('quota'),
                    versioning=self.get_argument('versioning'),
                    metadata=self.get_argument('metadata'))
            else:
                self.client.create_directory(self.path)
        except ClientError as err:
            raiseCLIError(err)

@command()
class store_copy(_store_container_command):
    """Copy an object"""

    def update_parser(self, parser):
        super(store_copy, self).update_parser(parser)
        parser.add_argument('--source-version', action='store', dest='source_version', default=None,
            help='copy specific version')
        parser.add_argument('--public', action='store_true', dest='public', default=False,
            help='make object publicly accessible')
        parser.add_argument('--content-type', action='store', dest='content_type', default=None,
            help='change object\'s content type')
        parser.add_argument('--delimiter', action='store', dest='delimiter', default=None,
            help=u'mass copy objects with path staring with src_object + delimiter')
        parser.add_argument('-r', action='store_true', dest='recursive', default=False,
            help='mass copy with delimiter /')

    def getdelimiter(self):
        if getattr(self.args, 'recursive'):
            return '/'
        return getattr(self.args, 'delimiter')

    def main(self, source_container___path, destination_container____path__):
        super(self.__class__, self).main(source_container___path, path_is_optional=False)
        try:
            dst = destination_container____path__.split(':')
            dst_cont = dst[0]
            dst_path = dst[1] if len(dst) > 1 else False
            self.client.copy_object(src_container = self.container, src_object = self.path,
                dst_container = dst_cont, dst_object = dst_path,
                source_version=getattr(self.args, 'source_version'),
                public=getattr(self.args, 'public'),
                content_type=getattr(self.args,'content_type'), delimiter=self.getdelimiter())
        except ClientError as err:
            raiseCLIError(err)

@command()
class store_move(_store_container_command):
    """Copy an object"""

    def update_parser(self, parser):
        super(store_move, self).update_parser(parser)
        parser.add_argument('--source-version', action='store', dest='source_version', default=None,
            help='copy specific version')
        parser.add_argument('--public', action='store_true', dest='public', default=False,
            help='make object publicly accessible')
        parser.add_argument('--content-type', action='store', dest='content_type', default=None,
            help='change object\'s content type')
        parser.add_argument('--delimiter', action='store', dest='delimiter', default=None,
            help=u'mass copy objects with path staring with src_object + delimiter')
        parser.add_argument('-r', action='store_true', dest='recursive', default=False,
            help='mass copy with delimiter /')

    def getdelimiter(self):
        if getattr(self.args, 'recursive'):
            return '/'
        return getattr(self.args, 'delimiter')

    def main(self, source_container___path, destination_container____path__):
        super(self.__class__, self).main(source_container___path, path_is_optional=False)
        try:
            dst = destination_container____path__.split(':')
            dst_cont = dst[0]
            dst_path = dst[1] if len(dst) > 1 else False
            self.client.move_object(src_container = self.container, src_object = self.path,
                dst_container = dst_cont, dst_object = dst_path,
                source_version=getattr(self.args, 'source_version'),
                public=getattr(self.args, 'public'),
                content_type=getattr(self.args,'content_type'), delimiter=self.getdelimiter())
        except ClientError as err:
            raiseCLIError(err)

@command()
class store_append(_store_container_command):
    """Append local file to (existing) remote object"""

    def main(self, local_path, container___path):
        super(self.__class__, self).main(container___path, path_is_optional=False)
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
        super(self.__class__, self).main(container___path, path_is_optional=False)
        try:
            self.client.truncate_object(self.path, size)
        except ClientError as err:
            raiseCLIError(err)

@command()
class store_overwrite(_store_container_command):
    """Overwrite part (from start to end) of a remote file"""

    def main(self, local_path, container___path, start, end):
        super(self.__class__, self).main(container___path, path_is_optional=False)
        try:
            f = open(local_path, 'r')
            upload_cb = self.progress('Overwritting blocks')
            self.client.overwrite_object(object=self.path, start=start, end=end,
                source_file=f, upload_cb = upload_cb)
        except ClientError as err:
            raiseCLIError(err)

@command()
class store_manifest(_store_container_command):
    """Create a remote file with uploaded parts by manifestation"""

    def update_parser(self, parser):
        super(self.__class__, self).update_parser(parser)
        parser.add_argument('--etag', action='store', dest='etag', default=None,
            help='check written data')
        parser.add_argument('--content-encoding', action='store', dest='content_encoding',
            default=None, help='provide the object MIME content type')
        parser.add_argument('--content-disposition', action='store', dest='content_disposition',
            default=None, help='provide the presentation style of the object')
        parser.add_argument('--content-type', action='store', dest='content_type', default=None,
            help='create object with specific content type')
        parser.add_argument('--sharing', action='store', dest='sharing', default=None,
            help='define sharing object policy ( "read=user1,grp1,user2,... write=user1,grp2,...')
        parser.add_argument('--public', action='store_true', dest='public', default=False,
            help='make object publicly accessible')

    def getsharing(self, orelse={}):
        permstr = getattr(self.args, 'sharing')
        if permstr is None:
            return orelse
        perms = {}
        for p in permstr.split(' '):
            (key, val) = p.split('=')
            if key.lower() not in ('read', 'write'):
                raise CLIError(message='in --sharing: Invalid permition key', importance=1)
            val_list = val.split(',')
            if not perms.has_key(key):
                perms[key]=[]
            for item in val_list:
                if item not in perms[key]:
                    perms[key].append(item)
        return perms
        
    def main(self, container___path):
        super(self.__class__, self).main(container___path, path_is_optional=False)
        try:
            self.client.create_object_by_manifestation(self.path,
                content_encoding=getattr(self.args, 'content_encoding'),
                content_disposition=getattr(self.args, 'content_disposition'),
                content_type=getattr(self.args, 'content_type'), sharing=self.getsharing(),
                public=getattr(self.args, 'public'))
        except ClientError as err:
            raiseCLIError(err)

@command()
class store_upload(_store_container_command):
    """Upload a file"""

    def update_parser(self, parser):
        super(self.__class__, self).update_parser(parser)
        parser.add_argument('--use_hashes', action='store_true', dest='use_hashes', default=False,
            help='provide hashmap file instead of data')
        parser.add_argument('--unchunked', action='store_true', dest='unchunked', default=False,
            help='avoid chunked transfer mode')
        parser.add_argument('--etag', action='store', dest='etag', default=None,
            help='check written data')
        parser.add_argument('--content-encoding', action='store', dest='content_encoding',
            default=None, help='provide the object MIME content type')
        parser.add_argument('--content-disposition', action='store', dest='content_disposition',
            default=None, help='provide the presentation style of the object')
        parser.add_argument('--content-type', action='store', dest='content_type', default=None,
            help='create object with specific content type')
        parser.add_argument('--sharing', action='store', dest='sharing', default=None,
            help='define sharing object policy ( "read=user1,grp1,user2,... write=user1,grp2,...')
        parser.add_argument('--public', action='store_true', dest='public', default=False,
            help='make object publicly accessible')
        parser.add_argument('--with-pool-size', action='store', dest='poolsize', default=None,
            help='Set the greenlet pool size (advanced)')

    def getsharing(self, orelse={}):
        permstr = getattr(self.args, 'sharing')
        if permstr is None:
            return orelse
        perms = {}
        for p in permstr.split(' '):
            (key, val) = p.split('=')
            if key.lower() not in ('read', 'write'):
                raise CLIError(message='in --sharing: Invalid permition key', importance=1)
            val_list = val.split(',')
            if not perms.has_key(key):
                perms[key]=[]
            for item in val_list:
                if item not in perms[key]:
                    perms[key].append(item)
        return perms

    def main(self, local_path, container____path__):
        super(self.__class__, self).main(container____path__)
        remote_path = local_path if self.path is None else self.path
        poolsize = getattr(self.args, 'poolsize')
        if poolsize is not None:
            self.POOL_SIZE = int(poolsize)
        try:
            with open(local_path) as f:
                if getattr(self.args, 'unchunked'):
                    self.client.upload_object_unchunked(remote_path, f,
                    etag=getattr(self.args, 'etag'), withHashFile=getattr(self.args, 'use_hashes'),
                    content_encoding=getattr(self.args, 'content_encoding'),
                    content_disposition=getattr(self.args, 'content_disposition'),
                    content_type=getattr(self.args, 'content_type'), sharing=self.getsharing(),
                    public=getattr(self.args, 'public'))
                else:
                    hash_cb = self.progress('Calculating block hashes')
                    upload_cb = self.progress('Uploading blocks')
                    self.client.upload_object(remote_path, f, hash_cb=hash_cb, upload_cb=upload_cb,
                    content_encoding=getattr(self.args, 'content_encoding'),
                    content_disposition=getattr(self.args, 'content_disposition'),
                    content_type=getattr(self.args, 'content_type'), sharing=self.getsharing(),
                    public=getattr(self.args, 'public'))
        except ClientError as err:
            raiseCLIError(err)
        print 'Upload completed'

@command()
class store_download(_store_container_command):
    """Download a file"""

    def update_parser(self, parser):
        super(self.__class__, self).update_parser(parser)
        parser.add_argument('--no-progress-bar', action='store_true', dest='no_progress_bar',
            default=False, help='Dont display progress bars')
        parser.add_argument('--resume', action='store_true', dest='resume', default=False,
            help='Resume a previous download instead of overwritting it')
        parser.add_argument('--range', action='store', dest='range', default=None,
            help='show range of data')
        parser.add_argument('--if-match', action='store', dest='if_match', default=None,
            help='show output if ETags match')
        parser.add_argument('--if-none-match', action='store', dest='if_none_match', default=None,
            help='show output if ETags don\'t match')
        parser.add_argument('--if-modified-since', action='store', dest='if_modified_since',
            default=None, help='show output if modified since then')
        parser.add_argument('--if-unmodified-since', action='store', dest='if_unmodified_since',
            default=None, help='show output if not modified since then')
        parser.add_argument('--object-version', action='store', dest='object_version', default=None,
            help='get the specific version')
        parser.add_argument('--with-pool-size', action='store', dest='poolsize', default=None,
            help='Set the greenlet pool size (advanced)')

    def main(self, container___path, local_path=None):
        super(self.__class__, self).main(container___path, path_is_optional=False)

        #setup output stream
        parallel = False
        if local_path is None:
            out = stdout
        else:
            try:
                if hasattr(self.args, 'resume') and getattr(self.args, 'resume'):
                    out=open(local_path, 'rwb+')
                else:
                    out=open(local_path, 'wb+')
            except IOError as err:
                raise CLIError(message='Cannot write to file %s - %s'%(local_path,unicode(err)),
                    importance=1)
        download_cb = None if getattr(self.args, 'no_progress_bar') \
        else self.progress('Downloading')
        poolsize = getattr(self.args, 'poolsize')
        if poolsize is not None:
            self.POOL_SIZE = int(poolsize)

        try:
            self.client.download_object(self.path, out, download_cb,
                range=getattr(self.args, 'range'), version=getattr(self.args,'object_version'),
                if_match=getattr(self.args, 'if_match'), resume=getattr(self.args, 'resume'),
                if_none_match=getattr(self.args, 'if_none_match'),
                if_modified_since=getattr(self.args, 'if_modified_since'),
                if_unmodified_since=getattr(self.args, 'if_unmodified_since'))
        except ClientError as err:
            raiseCLIError(err)
        except KeyboardInterrupt:
            print('\ndownload canceled by user')
            if local_path is not None:
                print('to resume, re-run with --resume')
        print

@command()
class store_hashmap(_store_container_command):
    """Get the hashmap of an object"""

    def update_parser(self, parser):
        super(self.__class__, self).update_parser(parser)
        parser.add_argument('--if-match', action='store', dest='if_match', default=None,
            help='show output if ETags match')
        parser.add_argument('--if-none-match', action='store', dest='if_none_match', default=None,
            help='show output if ETags dont match')
        parser.add_argument('--if-modified-since', action='store', dest='if_modified_since',
            default=None, help='show output if modified since then')
        parser.add_argument('--if-unmodified-since', action='store', dest='if_unmodified_since',
            default=None, help='show output if not modified since then')
        parser.add_argument('--object-version', action='store', dest='object_version', default=None,
            help='get the specific version')

    def main(self, container___path):
        super(self.__class__, self).main(container___path, path_is_optional=False)
        try:
            data = self.client.get_object_hashmap(self.path,
                version=getattr(self.args, 'object_version'),
                if_match=getattr(self.args, 'if_match'),
                if_none_match=getattr(self.args, 'if_none_match'),
                if_modified_since=getattr(self.args, 'if_modified_since'),
                if_unmodified_since=getattr(self.args, 'if_unmodified_since'))
        except ClientError as err:
            raiseCLIError(err)
        print_dict(data)

@command()
class store_delete(_store_container_command):
    """Delete a container [or an object]"""

    def update_parser(self, parser):
        super(self.__class__, self).update_parser(parser)
        parser.add_argument('--until', action='store', dest='until', default=None,
            help='remove history until that date')
        parser.add_argument('--format', action='store', dest='format', default='%d/%m/%Y %H:%M:%S',
            help='format to parse until date (default: d/m/Y H:M:S)')
        parser.add_argument('--delimiter', action='store', dest='delimiter',
            default=None, 
            help='mass delete objects with path staring with <object><delimiter>')
        parser.add_argument('-r', action='store_true', dest='recursive', default=False,
            help='empty dir or container and delete (if dir)')
    
    def getuntil(self, orelse=None):
        if hasattr(self.args, 'until'):
            import time
            until = getattr(self.args, 'until')
            if until is None:
                return None
            format = getattr(self.args, 'format')
            try:
                t = time.strptime(until, format)
            except ValueError as err:
                raise CLIError(message='in --until: '+unicode(err), importance=1)
            return int(time.mktime(t))
        return orelse

    def getdelimiter(self, orelse=None):
        try:
            dlm = getattr(self.args, 'delimiter')
            if dlm is None:
                return '/' if getattr(self.args, 'recursive') else orelse
        except AttributeError:
            return orelse
        return dlm

    def main(self, container____path__):
        super(self.__class__, self).main(container____path__)
        try:
            if self.path is None:
                self.client.del_container(until=self.getuntil(), delimiter=self.getdelimiter())
            else:
                #self.client.delete_object(self.path)
                self.client.del_object(self.path, until=self.getuntil(),
                    delimiter=self.getdelimiter())
        except ClientError as err:
            raiseCLIError(err)

@command()
class store_purge(_store_container_command):
    """Purge a container"""
    
    def main(self, container):
        super(self.__class__, self).main(container)
        try:
            self.client.purge_container()
        except ClientError as err:
            raiseCLIError(err)

@command()
class store_publish(_store_container_command):
    """Publish an object"""

    def main(self, container___path):
        super(self.__class__, self).main(container___path, path_is_optional=False)
        try:
            self.client.publish_object(self.path)
        except ClientError as err:
            raiseCLIError(err)

@command()
class store_unpublish(_store_container_command):
    """Unpublish an object"""

    def main(self, container___path):
        super(self.__class__, self).main(container___path, path_is_optional=False)
        try:
            self.client.unpublish_object(self.path)
        except ClientError as err:
            raiseCLIError(err)

@command()
class store_permitions(_store_container_command):
    """Get object read/write permitions"""

    def main(self, container___path):
        super(self.__class__, self).main(container___path, path_is_optional=False)
        try:
            reply = self.client.get_object_sharing(self.path)
            print_dict(reply)
        except ClientError as err:
            raiseCLIError(err)

@command()
class store_setpermitions(_store_container_command):
    """Set sharing permitions"""

    def format_permition_dict(self,permitions):
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
        return (read,write)

    def main(self, container___path, *permitions):
        super(self.__class__, self).main(container___path, path_is_optional=False)
        (read, write) = self.format_permition_dict(permitions)
        try:
            self.client.set_object_sharing(self.path,
                read_permition=read, write_permition=write)
        except ClientError as err:
            raiseCLIError(err)

@command()
class store_delpermitions(_store_container_command):
    """Delete all sharing permitions"""

    def main(self, container___path):
        super(self.__class__, self).main(container___path, path_is_optional=False)
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
        super(self.__class__, self).update_parser(parser)
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

        detail = getattr(self.args, 'detail')
        try:
            if self.container is None:
                print(bold(self.client.account))
                if detail:
                    reply = self.client.get_account_info(until=self.getuntil())
                else:
                    reply = self.client.get_account_meta(until=self.getuntil())
                    reply = pretty_keys(reply, '-')
            elif self.path is None:
                print(bold(self.client.account+': '+self.container))
                if detail:
                    reply = self.client.get_container_info(until = self.getuntil())
                else:
                    cmeta = self.client.get_container_meta(until=self.getuntil())
                    ometa = self.client.get_container_object_meta(until=self.getuntil())
                    reply = {'container-meta':pretty_keys(cmeta, '-'),
                        'object-meta':pretty_keys(ometa, '-')}
            else:
                print(bold(self.client.account+': '+self.container+':'+self.path))
                version=getattr(self.args, 'object_version')
                if detail:
                    reply = self.client.get_object_info(self.path, version = version)
                else:
                    reply = self.client.get_object_meta(self.path, version=version)
                    reply = pretty_keys(pretty_keys(reply, '-'))
        except ClientError as err:
            raiseCLIError(err)
        print_dict(reply)

@command()
class store_setmeta(_store_container_command):
    """Set a new metadatum for account [, container [or object]]"""

    def main(self, metakey___metaval, container____path__=None):
        super(self.__class__, self).main(container____path__)
        try:
            metakey, metavalue = metakey___metaval.split(':')
        except ValueError:
            raise CLIError(message='Meta variables should be formated as metakey:metavalue',
                importance=1)
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

@command()
class store_sharers(_store_account_command):
    """List the accounts that share objects with default account"""

    def update_parser(self, parser):
        super(store_sharers, self).update_parser(parser)
        parser.add_argument('-l', action='store_true', dest='detail', default=False,
            help='show detailed output')
        parser.add_argument('-n', action='store',  dest='limit', default=10000,
            help='show limited output')
        parser.add_argument('--marker', action='store', dest='marker', default=None,
            help='show output greater then marker')

    def main(self):
        super(self.__class__, self).main()
        try:
            accounts = self.client.get_sharing_accounts(marker=getattr(self.args, 'marker'))
        except ClientError as err:
            raiseCLIError(err)

        for acc in accounts:
            stdout.write(bold(acc['name'])+' ')
            if getattr(self.args, 'detail'):
                print_dict(acc, exclude='name', ident=18)
        if not getattr(self.args, 'detail'):
            print

@command()
class store_versions(_store_container_command):
    """Get the version list of an object"""

    def main(self, container___path):
        super(store_versions, self).main(container___path)
        try:
            versions = self.client.get_object_versionlist(self.path)
        except ClientError as err:
            raise CLIError(err)

        print('%s:%s versions'%(self.container,self.path))
        for vitem in versions:
            t = localtime(float(vitem[1]))
            vid = bold(unicode(vitem[0]))
            print('\t%s \t(%s)'%(vid, strftime('%d-%m-%Y %H:%M:%S', t)))
