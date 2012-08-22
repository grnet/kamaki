#!/usr/bin/env python

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
# or implied, of GRNET S.A.

from kamaki.cli import command, CLIError
from .utils import dict2file, list2file
from .pithos_cli import _store_container_command

#from getpass import getuser
#from optparse import OptionParser
#from os import environ
from sys import stdout#argv, exit, stdin, stdout
#from datetime import datetime

from .pithos_sh_lib.client import Pithos_Client, Fault
#from .pithos_sh_lib.util import get_user, get_auth, get_url
from .pithos_sh_lib.transfer import download, cat#,upload

#import json
#import logging
import types
#import re
#import time as _time
#import os

class _pithos_sh_container_command(_store_container_command):

    def update_parser(self, parser):
        super(_pithos_sh_container_command, self).update_parser(parser)

    def main(self, container_with_path, path_is_optional=True):
        super(_pithos_sh_container_command, self).main(container_with_path, path_is_optional)
        self.client = Pithos_Client(self.base_url, self.token, self.account)

  
def _build_args(arglist, attrs):
    args = {}
    for a in [a for a in attrs if getattr(arglist, a)]:
        args[a] = getattr(arglist, a)
    return args

@command()
class store_download(_pithos_sh_container_command):
    """Download/show an object"""

    def update_parser(self, parser):
        super(store_download, self).update_parser(parser)
        parser.add_argument('-l', action='store_true', dest='detail', default=False,
            help='show detailed output')
        parser.add_argument('--range', action='store', dest='range', default=None,
            help='show range of data')
        parser.add_argument('--if-range', action='store', dest='if_range', default=None,
            help='show range of data')
        parser.add_argument('--if-match', action='store', dest='if_match', default=None,
            help='show output if ETags match')
        parser.add_argument('--if-none-match', action='store', dest='if_none_match', default=None,
            help='show output if ETags don\'t match')
        parser.add_argument('--if-modified-since', action='store', dest='if_modified_since',
            default=None, help='show output if modified since then')
        parser.add_argument('--if-unmodified-since', action='store', dest='if_unmodified_since',
            default=None, help='show output if not modified since then')
        parser.add_argument('--object-version', action='store', dest='object-version', default=None,
            help='get the specific version')
        parser.add_argument('--versionlist', action='store_true', dest='versionlist', default=False,
            help='get the full object version list')
        parser.add_argument('--hashmap', action='store_true', dest='hashmap', default=False,
            help='get the object hashmap instead')
    
    def main(self, container___path, outputFile=None):
        super(store_download, self).main(container___path)

        #prepare attributes and headers
        attrs = ['if_match', 'if_none_match', 'if_modified_since',
                 'if_unmodified_since', 'hashmap']
        args = _build_args(self.args, attrs)
        args['format'] = 'json' if hasattr(self.args,'detail') else 'text'
        if getattr(self.args, 'range') is not None:
            args['range'] = 'bytes=%s' % getattr(self.args,'range')
        if getattr(self.args, 'if_range'):
            args['if-range'] = 'If-Range:%s' % getattr(self.args, 'if_range')

        #branch through options
        if getattr(self.args,'versionlist'):
            try:
                args.pop('detail')
            except KeyError:
                pass
            args.pop('format')
            data=self.client.retrieve_object_versionlist(self.container, self.path, **args)
        elif getattr(self.args,'object-version'):
            data = self.client.retrieve_object_version(self.container, self.path,
                version=getattr(self.args, 'object-version'), **args)
        elif getattr(self.args, 'hashmap'):
            try:
                args.pop('detail')
            except KeyError:
                pass
            data=self.client.retrieve_object_hashmap(self.container, self.path, **args)
        elif outputFile is None:
            cat(self.client, self.container, self.path)
        else:
            download(self.client, self.container, self.path, outputFile)
            return

        f = stdout if outputFile is None else open(outputFile, 'w')
        if type(data) is dict:
            dict2file(data, f)
        elif type(data) is list:
            list2file(data, f)
        else:
            f.write(unicode(data)+'\n')
        f.close()

"""
@command()
class store_CopyObject(object):
    ""cop an object to a different location""
    syntax = '<src container>/<src object> [<dst container>/]<dst object> [key=val] [...]'

    def main(self):
        pass
    
    def add_options(self, parser):
        parser.add_option('--version', action='store',
                          dest='version', default=False,
                          help='copy specific version')
        parser.add_option('--public', action='store_true',
                          dest='public', default=False,
                          help='make object publicly accessible')
        parser.add_option('--content-type', action='store',
                          dest='content_type', default=None,
                          help='change object\'s content type')
        parser.add_option('--delimiter', action='store', 
                          dest='delimiter', default=None,
                          help='mass copy objects with path staring with <src object> + delimiter')
        parser.add_option('-r', action='store_true',
                          dest='recursive', default=False,
                          help='mass copy with delimiter /')
    
    def execute(self, src, dst, *args):
        src_container, sep, src_object = src.partition('/')
        dst_container, sep, dst_object = dst.partition('/')
        
        #prepare user defined meta
        meta = {}
        for arg in args:
            key, sep, val = arg.partition('=')
            meta[key] = val
        
        if not sep:
            dst_container = src_container
            dst_object = dst
        
        args = {'content_type':self.content_type} if self.content_type else {}
        if self.delimiter:
        	args['delimiter'] = self.delimiter
        elif self.recursive:
        	args['delimiter'] = '/'
        self.client.copy_object(src_container, src_object, dst_container,
                                dst_object, meta, self.public, self.version,
                                **args)

@command()
class store_UpdateObject(object):
    ""update object metadata/data (default mode: append)""
    syntax = '<container>/<object> path [key=val] [...]'

    def main(self):
        pass
    
    def update_parser(self, parser):
        super(store_UpdateObject, self).update_parser(parser)
        parser.add_argument('-a', action='store_true', dest='append',
                          default=True, help='append data')
        parser.add_argument('--offset', action='store',
                          dest='offset',
                          default=None, help='starting offest to be updated')
        parser.add_argument('--range', action='store', dest='content_range',
                          default=None, help='range of data to be updated')
        parser.add_argument('--chunked', action='store_true', dest='chunked',
                          default=False, help='set chunked transfer mode')
        parser.add_argument('--content-encoding', action='store',
                          dest='content_encoding', default=None,
                          help='provide the object MIME content type')
        parser.add_argument('--content-disposition', action='store', 
                          dest='content_disposition', default=None,
                          help='provide the presentation style of the object')
        parser.add_argument('--manifest', action='store', 
                          dest='x_object_manifest', default=None,
                          help='use for large file support')        
        parser.add_argument('--sharing', action='store',
                          dest='x_object_sharing', default=None,
                          help='define sharing object policy')
        parser.add_argument('--nosharing', action='store_true',
                          dest='no_sharing', default=None,
                          help='clear object sharing policy')
        parser.add_argument('-f', action='store',
                          dest='srcpath', default=None,
                          help='file descriptor to read from: pass - for standard input')
        parser.add_argument('--public', action='store_true',
                          dest='x_object_public', default=False,
                          help='make object publicly accessible')
        parser.add_argument('--replace', action='store_true',
                          dest='replace', default=False,
                          help='override metadata')
    
    def execute(self, path, *args):
        if path.find('=') != -1:
            raise Fault('Missing path argument')
        
        #prepare user defined meta
        meta = {}
        for arg in args:
            key, sep, val = arg.partition('=')
            meta[key] = val
        
        
        attrs = ['content_encoding', 'content_disposition', 'x_object_sharing',
                 'x_object_public', 'x_object_manifest', 'replace', 'offset',
                 'content_range']
        args = self._build_args(attrs)
        
        if self.no_sharing:
            args['x_object_sharing'] = ''
        
        container, sep, object = path.partition('/')
        
        f = None
        if self.srcpath:
            f = open(self.srcpath) if self.srcpath != '-' else stdin
        
        if self.chunked:
            self.client.update_object_using_chunks(container, object, f,
                                                    meta=meta, **args)
        else:
            self.client.update_object(container, object, f, meta=meta, **args)
        if f:
            f.close()

@command()
class store_MoveObject(object):
    ""move an object to a different location""
    syntax = '<src container>/<src object> [<dst container>/]<dst object>'

    def main(self):
        pass
    
    def update_parser(self, parser):
        super(store_MoveObject, self).update_parser(parser)
        parser.add_argument('--public', action='store_true',
                          dest='public', default=False,
                          help='make object publicly accessible')
        parser.add_argument('--content-type', action='store',
                          dest='content_type', default=None,
                          help='change object\'s content type')
        parser.add_argument('--delimiter', action='store', 
                          dest='delimiter', default=None,
                          help='mass move objects with path staring with <src object> + delimiter')
        parser.add_argument('-r', action='store_true',
                          dest='recursive', default=False,
                          help='mass move objects with delimiter /')
    
    def execute(self, src, dst, *args):
        src_container, sep, src_object = src.partition('/')
        dst_container, sep, dst_object = dst.partition('/')
        if not sep:
            dst_container = src_container
            dst_object = dst
        
        #prepare user defined meta
        meta = {}
        for arg in args:
            key, sep, val = arg.partition('=')
            meta[key] = val
        
        args = {'content_type':self.content_type} if self.content_type else {}
        if self.delimiter:
        	args['delimiter'] = self.delimiter
        elif self.recursive:
        	args['delimiter'] = '/'
        self.client.move_object(src_container, src_object, dst_container,
                                dst_object, meta, self.public, **args)

@command()
class store_SharingObject(object):
    ""list user accounts sharing objects with the user""
    syntax = 'list users sharing objects with the user'
    
    def main(self):
        pass
    
    def update_parser(self, parser):
        super(store_SharingObject, self).update_parser(parser)
        parser.add_argument('-l', action='store_true', dest='detail',
                          default=False, help='show detailed output')
        parser.add_argument('-n', action='store',  dest='limit',
                          default=10000, help='show limited output')
        parser.add_argument('--marker', action='store', 
                          dest='marker', default=None,
                          help='show output greater then marker')
        
    
    def execute(self):
        attrs = ['limit', 'marker']
        args = self._build_args(attrs)
        args['format'] = 'json' if self.detail else 'text'
        
        print_list(self.client.list_shared_by_others(**args))

@command()
class store_Receive(object):
    ""download object to file""
    syntax = '<container>/<object> <file>'
    
    def main(self):
        pass

    def execute(self, path, file):
        container, sep, object = path.partition('/')
        download(self.client, container, object, file)
"""