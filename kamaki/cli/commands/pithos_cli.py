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
from kamaki.cli.argument import FlagArgument, ValueArgument, IntArgument
#set_api_description('store', 'Pithos+ storage commands')
API_DESCRIPTION = dict(store='Pithos+ storage commands')
from kamaki.clients.pithos import PithosClient, ClientError
from colors import bold
from sys import stdout, exit
import signal
from time import localtime, strftime, strptime, mktime
from datetime import datetime as dtm

from progress.bar import IncrementalBar

#Argument functionality
class DelimiterArgument(ValueArgument):
    def __init__(self, caller_obj, help='', parsed_name=None, default=None):
        super(DelimiterArgument, self).__init__(help, parsed_name, default)
        self.caller_obj = caller_obj

    @property 
    def value(self):
        if self.caller_obj.get_argument('recursive'):
            return '/'
        return getattr(self, '_value', self.default)
    @value.setter 
    def value(self, newvalue):
        self._value = newvalue

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
    @value.setter
    def value(self, newvalue):
        if newvalue is None:
            self._value = self.default
        self._value = newvalue



class ProgressBarArgument(FlagArgument):

    def __init__(self, help='', parsed_name='', default=True):
        self.suffix = '%(percent)d%%'
        super(ProgressBarArgument, self).__init__(help, parsed_name, default)
        self.bar = IncrementalBar()

    @property 
    def value(self):
        return getattr(self, '_value', self.default)
    @value.setter 
    def value(self, newvalue):
        """By default, it is on (True)"""
        self._value = not newvalue
    def get_generator(self, message, message_len=25):
        bar = ProgressBar()
        return bar.get_generator(message, message_len)

class ProgressBar(IncrementalBar):
    def get_generator(self, message, message_len):
        def progress_gen(n):
            self.msg = message.ljust(message_len)
            for i in self.iter(range(n)):
                yield
            yield
        return progress_gen

class SharingArgument(ValueArgument):
    @property 
    def value(self):
        return getattr(self, '_value', self.default)
    @value.setter
    def value(self, newvalue):
        perms = {}
        try:
            permlist = newvalue.split(' ')
        except AttributeError:
            return
        for p in permlist:
            try:
                (key,val) = p.split('=')
            except ValueError:
                raise CLIError(message='Error in --sharing', details='Incorrect format', importance=1)
            if key.lower() not in ('read', 'write'):
                raise CLIError(message='Error in --sharing', details='Invalid permition key %s'%key, importance=1)
            val_list = val.split(',')
            if not perms.has_key(key):
                perms[key]=[]
            for item in val_list:
                if item not in perms[key]:
                    perms[key].append(item)
        self._value = perms

class RangeArgument(ValueArgument):
    @property 
    def value(self):
        return getattr(self, '_value', self.default)
    @value.setter
    def value(self, newvalue):
        if newvalue is None:
            self._value = self.default
            return
        (start, end) = newvalue.split('_')
        (start, end) = (int(start), int(end))
        self._value = '%s-%s'%(start, end)

class DateArgument(ValueArgument):
    DATE_FORMATS = ["%a %b %d %H:%M:%S %Y",
        "%A, %d-%b-%y %H:%M:%S GMT",
        "%a, %d %b %Y %H:%M:%S GMT"]

    INPUT_FORMATS = DATE_FORMATS + ["%d-%m-%Y", "%H:%M:%S %d-%m-%Y"]

    @property 
    def value(self):
        return getattr(self, '_value', self.default)
    @value.setter
    def value(self, newvalue):
        if newvalue is None:
            return
        self._value = self.format_date(newvalue)

    def format_date(self, datestr):
        for format in self.INPUT_FORMATS:
            try:
                t = dtm.strptime(datestr, format)
            except ValueError:
                continue
            self._value = t.strftime(self.DATE_FORMATS[0])
            return
        raise CLIError('Date Argument Error',
            details='%s not a valid date. correct formats:\n\t%s'%(datestr, self.INPUT_FORMATS))

#Command specs
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

    def generator(self, message):
       return None 

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
        self.arguments['limit'] = IntArgument('show limited output', '-n')
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
        self.arguments['until'] = DateArgument('show metadata until then', '--until')
        self.arguments['format'] = ValueArgument('format to parse until data (default: d/m/Y H:M:S',
            '--format')
        self.arguments['shared'] = FlagArgument('show only shared', '--shared')
        self.arguments['public'] = FlagArgument('show only public', '--public')

    def print_objects(self, object_list):
        import sys
        try:
            limit = self.get_argument('show_size')
            limit = int(limit)
        except (AttributeError, TypeError):
            limit = len(object_list) + 1
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
        except (AttributeError, TypeError):
            limit = len(container_list)+1
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
        self.arguments['quota'] = IntArgument('set default container quota', '--quota')
        self.arguments['meta'] = MetaArgument('set container metadata', '---meta')

    def main(self, container____directory__):
        super(self.__class__, self).main(container____directory__)
        try:
            if self.path is None:
                self.client.container_put(quota=self.get_argument('quota'),
                    versioning=self.get_argument('versioning'),
                    metadata=self.get_argument('meta'))
            else:
                self.client.create_directory(self.path)
        except ClientError as err:
            raiseCLIError(err)

@command()
class store_copy(_store_container_command):
    """Copy an object"""

    def __init__(self, arguments={}):
        super(self.__class__, self).__init__(arguments)
        self.arguments['source_version']=ValueArgument('copy specific version', '--source-version')
        self.arguments['public']=ValueArgument('make object publicly accessible', '--public')
        self.arguments['content_type']=ValueArgument('change object\'s content type',
            '--content-type')
        self.arguments['delimiter']=DelimiterArgument(self, parsed_name='--delimiter',
            help = u'mass copy objects with path staring with src_object + delimiter')
        self.arguments['recursive']=FlagArgument('mass copy with delimiter /', ('-r','--recursive'))

    def main(self, source_container___path, destination_container____path__):
        super(self.__class__, self).main(source_container___path, path_is_optional=False)
        try:
            dst = destination_container____path__.split(':')
            dst_cont = dst[0]
            dst_path = dst[1] if len(dst) > 1 else False
            self.client.copy_object(src_container = self.container, src_object = self.path,
                dst_container = dst_cont, dst_object = dst_path,
                source_version=self.get_argument('source_version'),
                public=self.get_argument('public'),
                content_type=self.get_argument('content_type'),
                delimiter=self.get_argument('delimiter'))
        except ClientError as err:
            raiseCLIError(err)

@command()
class store_move(_store_container_command):
    """Copy an object"""

    def __init__(self, arguments={}):
        super(self.__class__, self).__init__(arguments)

        self.arguments['source_version']=ValueArgument('copy specific version', '--source-version')
        self.arguments['public']=FlagArgument('make object publicly accessible', '--public')
        self.arguments['content_type']=ValueArgument('change object\'s content type',
            '--content-type')
        self.arguments['delimiter']=DelimiterArgument(self, parsed_name='--delimiter',
            help = u'mass copy objects with path staring with src_object + delimiter')
        self.arguments['recursive']=FlagArgument('mass copy with delimiter /', ('-r','--recursive'))

    def main(self, source_container___path, destination_container____path__):
        super(self.__class__, self).main(source_container___path, path_is_optional=False)
        try:
            dst = destination_container____path__.split(':')
            dst_cont = dst[0]
            dst_path = dst[1] if len(dst) > 1 else False
            self.client.move_object(src_container = self.container, src_object = self.path,
                dst_container = dst_cont, dst_object = dst_path,
                source_version=self.get_argument('source_version'),
                public=self.get_argument('public'),
                content_type=self.get_argument('content_type'),
                delimiter=self.get_argument('delimiter'))
        except ClientError as err:
            raiseCLIError(err)

@command()
class store_append(_store_container_command):
    """Append local file to (existing) remote object"""

    def __init__(self, arguments={}):
        super(self.__class__, self).__init__(arguments)
        self.arguments['progress_bar'] = ProgressBarArgument('do not show progress bar', '--no-progress-bar')

    def main(self, local_path, container___path):
        super(self.__class__, self).main(container___path, path_is_optional=False)
        try:
            f = open(local_path, 'r')
            upload_cb = self.arguments['progress_bar'].get_generator('Appending blocks')
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

    def __init__(self, arguments={}):
        super(self.__class__, self).__init__(arguments)
        self.arguments['progress_bar'] = ProgressBarArgument('do not show progress bar',
            '--no-progress-bar')

    def main(self, local_path, container___path, start, end):
        super(self.__class__, self).main(container___path, path_is_optional=False)
        try:
            f = open(local_path, 'r')
            upload_cb = self.arguments['progress_bar'].get_generator('Overwritting blocks')
            self.client.overwrite_object(object=self.path, start=start, end=end,
                source_file=f, upload_cb = upload_cb)
        except ClientError as err:
            raiseCLIError(err)

@command()
class store_manifest(_store_container_command):
    """Create a remote file with uploaded parts by manifestation"""

    def __init__(self, arguments={}):
        super(self.__class__, self).__init__(arguments)
        self.arguments['etag'] = ValueArgument('check written data', '--etag')
        self.arguments['content_encoding']=ValueArgument('provide the object MIME content type',
            '--content-encoding')
        self.arguments['content_disposition'] = ValueArgument('provide the presentation style of the object',
            '--content-disposition')
        self.arguments['content_type']=ValueArgument('create object with specific content type',
            '--content-type')
        self.arguments['sharing']=SharingArgument(parsed_name='--sharing',
            help='define sharing object policy ( "read=user1,grp1,user2,... write=user1,grp2,...')
        self.arguments['public']=FlagArgument('make object publicly accessible', '--public')
        
    def main(self, container___path):
        super(self.__class__, self).main(container___path, path_is_optional=False)
        try:
            self.client.create_object_by_manifestation(self.path,
                content_encoding=self.get_argument('content_encoding'),
                content_disposition=self.get_argument('content_disposition'),
                content_type=self.get_argument('content_type'),
                sharing=self.get_argument('sharing'), public=self.get_argument('public'))
        except ClientError as err:
            raiseCLIError(err)

@command()
class store_upload(_store_container_command):
    """Upload a file"""

    def __init__(self, arguments={}):
        super(self.__class__, self).__init__(arguments)
        self.arguments['use_hashes'] = FlagArgument('provide hashmap file instead of data',
            '--use-hashes')
        self.arguments['etag'] = ValueArgument('check written data', '--etag')
        self.arguments['unchunked'] = FlagArgument('avoid chunked transfer mode', '--unchunked')
        self.arguments['content_encoding']=ValueArgument('provide the object MIME content type',
            '--content-encoding')
        self.arguments['content_disposition'] = ValueArgument('provide the presentation style of the object',
            '--content-disposition')
        self.arguments['content_type']=ValueArgument('create object with specific content type',
            '--content-type')
        self.arguments['sharing']=SharingArgument(parsed_name='--sharing',
            help='define sharing object policy ( "read=user1,grp1,user2,... write=user1,grp2,...')
        self.arguments['public']=FlagArgument('make object publicly accessible', '--public')
        self.arguments['poolsize']=IntArgument('set pool size', '--with-pool-size')
        self.arguments['progress_bar'] = ProgressBarArgument('do not show progress bar', '--no-progress-bar')

    def main(self, local_path, container____path__):
        super(self.__class__, self).main(container____path__)
        remote_path = local_path if self.path is None else self.path
        poolsize = self.get_argument('poolsize')
        if poolsize is not None:
            self.POOL_SIZE = poolsize
        try:
            with open(local_path) as f:
                if self.get_argument('unchunked'):
                    self.client.upload_object_unchunked(remote_path, f,
                    etag=self.get_argument('etag'), withHashFile=self.get_argument('use_hashes'),
                    content_encoding=self.get_argument('content_encoding'),
                    content_disposition=self.get_argument('content_disposition'),
                    content_type=self.get_argument('content_type'),
                    sharing=self.get_argument('sharing'), public=self.get_argument('public'))
                else:
                    hash_cb=self.arguments['progress_bar'].get_generator('Calculating block hashes')
                    upload_cb=self.arguments['progress_bar'].get_generator('Uploading')
                    self.client.upload_object(remote_path, f, hash_cb=hash_cb, upload_cb=upload_cb,
                    content_encoding=self.get_argument('content_encoding'),
                    content_disposition=self.get_argument('content_disposition'),
                    content_type=self.get_argument('content_type'),
                    sharing=self.get_argument('sharing'), public=self.get_argument('public'))
        except ClientError as err:
            raiseCLIError(err)
        print 'Upload completed'

@command()
class store_download(_store_container_command):
    """Download a file"""

    def __init__(self, arguments={}):
        super(self.__class__, self).__init__(arguments)
        self.arguments['resume'] = FlagArgument(parsed_name='--resume',
            help = 'Resume a previous download instead of overwritting it')
        self.arguments['range'] = RangeArgument('show range of data', '--range')
        self.arguments['if_match'] = ValueArgument('show output if ETags match', '--if-match')
        self.arguments['if_none_match'] = ValueArgument('show output if ETags match',
            '--if-none-match')
        self.arguments['if_modified_since'] = DateArgument('show output modified since then',
            '--if-modified-since')
        self.arguments['if_unmodified_since'] = DateArgument('show output unmodified since then',
            '--if-unmodified-since')
        self.arguments['object_version'] = ValueArgument('get the specific version',
            '--object-version')
        self.arguments['poolsize']=IntArgument('set pool size', '--with-pool-size')
        self.arguments['progress_bar'] = ProgressBarArgument('do not show progress bar',
            '--no-progress-bar')

    def main(self, container___path, local_path=None):
        super(self.__class__, self).main(container___path, path_is_optional=False)

        #setup output stream
        parallel = False
        if local_path is None:
            out = stdout
        else:
            try:
                if self.get_argument('resume'):
                    out=open(local_path, 'rwb+')
                else:
                    out=open(local_path, 'wb+')
            except IOError as err:
                raise CLIError(message='Cannot write to file %s - %s'%(local_path,unicode(err)),
                    importance=1)
        download_cb = self.arguments['progress_bar'].get_generator('Downloading')
        poolsize = self.get_argument('poolsize')
        if poolsize is not None:
            self.POOL_SIZE = int(poolsize)

        try:
            self.client.download_object(self.path, out, download_cb,
                range=self.get_argument('range'), version=self.get_argument('object_version'),
                if_match=self.get_argument('if_match'), resume=self.get_argument('resume'),
                if_none_match=self.get_argument('if_none_match'),
                if_modified_since=self.get_argument('if_modified_since'),
                if_unmodified_since=self.get_argument('if_unmodified_since'))
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

    def __init__(self, arguments={}):
        super(self.__class__, self).__init__(arguments)
        self.arguments['if_match'] = ValueArgument('show output if ETags match', '--if-match')
        self.arguments['if_none_match'] = ValueArgument('show output if ETags match',
            '--if-none-match')
        self.arguments['if_modified_since'] = DateArgument('show output modified since then',
            '--if-modified-since')
        self.arguments['if_unmodified_since'] = DateArgument('show output unmodified since then',
            '--if-unmodified-since')
        self.arguments['object_version'] = ValueArgument('get the specific version',
            '--object-version')

    def main(self, container___path):
        super(self.__class__, self).main(container___path, path_is_optional=False)
        try:
            data = self.client.get_object_hashmap(self.path,
                version=self.arguments('object_version'),
                if_match=self.arguments('if_match'),
                if_none_match=self.arguments('if_none_match'),
                if_modified_since=self.arguments('if_modified_since'),
                if_unmodified_since=self.arguments('if_unmodified_since'))
        except ClientError as err:
            raiseCLIError(err)
        print_dict(data)

@command()
class store_delete(_store_container_command):
    """Delete a container [or an object]"""

    def __init__(self, arguments={}):
        super(self.__class__, self).__init__(arguments)
        self.arguments['until'] = DateArgument('remove history until that date', '--until')
        self.arguments['recursive'] = FlagArgument('empty dir or container and delete (if dir)',
            '--recursive')
        self.arguments['delimiter'] = DelimiterArgument(self, parsed_name='--delimiter',
            help = 'mass delete objects with path staring with <object><delimiter>')

    def main(self, container____path__):
        super(self.__class__, self).main(container____path__)
        try:
            if self.path is None:
                self.client.del_container(until=self.get_argument('until'),
                    delimiter=self.get_argument('delimiter'))
            else:
                #self.client.delete_object(self.path)
                self.client.del_object(self.path, until=self.get_argument('until'),
                    delimiter=self.get_argument('delimiter'))
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

    def __init__(self, arguments = {}):
        super(self.__class__, self).__init__(arguments)
        self.arguments['detail'] = FlagArgument('show detailed output', '-l')
        self.arguments['until'] = DateArgument('show metadata until then', '--until')
        self.arguments['object_version'] = ValueArgument(parsed_name='--object-version',
            help='show specific version \ (applies only for objects)')

    def main(self, container____path__ = None):
        super(self.__class__, self).main(container____path__)

        detail = self.get_argument('detail')
        try:
            if self.container is None:
                print(bold(self.client.account))
                if detail:
                    reply = self.client.get_account_info(until=self.get_argument('until'))
                else:
                    reply = self.client.get_account_meta(until=self.get_argument('until'))
                    reply = pretty_keys(reply, '-')
            elif self.path is None:
                print(bold(self.client.account+': '+self.container))
                if detail:
                    reply = self.client.get_container_info(until = self.get_argument('until'))
                else:
                    cmeta = self.client.get_container_meta(until=self.get_argument('until'))
                    ometa = self.client.get_container_object_meta(until=self.get_argument('until'))
                    reply = {'container-meta':pretty_keys(cmeta, '-'),
                        'object-meta':pretty_keys(ometa, '-')}
            else:
                print(bold(self.client.account+': '+self.container+':'+self.path))
                version=self.get_argument('object_version')
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

    def __init__(self, arguments = {}):
        super(self.__class__, self).__init__(arguments)
        self.arguments['detail'] = FlagArgument('show detailed output', '-l')
        self.arguments['limit'] = IntArgument('show limited output', '--n', default=1000)
        self.arguments['marker'] = ValueArgument('show output greater then marker', '--marker')

    def main(self):
        super(self.__class__, self).main()
        try:
            accounts = self.client.get_sharing_accounts(marker=self.get_argument('marker'))
        except ClientError as err:
            raiseCLIError(err)

        for acc in accounts:
            stdout.write(bold(acc['name'])+' ')
            if self.get_argument('detail'):
                print_dict(acc, exclude='name', ident=18)
        if not self.get_argument('detail'):
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
