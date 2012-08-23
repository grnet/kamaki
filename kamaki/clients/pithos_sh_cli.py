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
from kamaki.utils import print_list
from .utils import dict2file, list2file
from .pithos_cli import _store_container_command, _store_account_command
from colors import bold

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

class _pithos_sh_account_command(_store_account_command):

    def update_parser(self, parser):
        super(_pithos_sh_account_command, self).update_parser(parser)

    def main(self):
        super(_pithos_sh_account_command, self).main()
        self.client = Pithos_Client(self.base_url, self.token, self.account)

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
class store_versions(_pithos_sh_container_command):
    """Get the version list of an object"""

    def main(self, container___path):
        super(store_versions, self).main(container___path)
        try:
            data = self.client.retrieve_object_versionlist(self.container, self.path)
        except Fault as err:
            raise CLIError(message=unicode(err), status=err.status)
        from time import localtime, strftime
        print('%s:%s version ids:'%(self.container,self.path))
        for vitem in data['versions']:
            t = localtime(float(vitem[1]))
            vid = bold(unicode(vitem[0]))
            print('\t%s \t(%s)'%(vid, strftime('%d-%m-%Y %H:%M:%S', t)))

@command()
class store_downloadz(_pithos_sh_container_command):
    """Download an object"""

    def update_parser(self, parser):
        super(store_downloadz, self).update_parser(parser)
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
    
    def main(self, container___path, outputFile=None):
        super(store_downloadz, self).main(container___path)

        #prepare attributes and headers
        attrs = ['if_match', 'if_none_match', 'if_modified_since',
                 'if_unmodified_since']
        args = _build_args(self.args, attrs)
        args['format'] = 'json' if hasattr(self.args,'detail') else 'text'
        if getattr(self.args, 'range') is not None:
            args['range'] = 'bytes=%s' % getattr(self.args,'range')
        if getattr(self.args, 'if_range'):
            args['if-range'] = 'If-Range:%s' % getattr(self.args, 'if_range')

        #branch through options
        try:
            if getattr(self.args,'object-version'):
                data = self.client.retrieve_object_version(self.container, self.path,
                    version=getattr(self.args, 'object-version'), **args)
            elif outputFile is None:
                cat(self.client, self.container, self.path)
                return
            else:
                download(self.client, self.container, self.path, outputFile)
                return
        except Fault as err:
            raise CLIError(message=unicode(err), status=err.status, importance=err.status/100)

        f = stdout if outputFile is None else open(outputFile, 'w')
        if type(data) is dict:
            dict2file(data, f)
        elif type(data) is list:
            list2file(data, f)
        else:
            f.write(unicode(data)+'\n')
        f.close()

@command()
class store_sharers(_pithos_sh_account_command):
    """list accounts who share objects with current account"""
    
    def update_parser(self, parser):
        super(store_sharers, self).update_parser(parser)
        parser.add_argument('-l', action='store_true', dest='detail', default=False,
            help='show detailed output')
        parser.add_argument('-n', action='store',  dest='limit', default=10000,
            help='show limited output')
        parser.add_argument('--marker', action='store', dest='marker', default=None,
            help='show output greater then marker')
        
    def main(self):
        super(store_sharers, self).main()
        attrs = ['limit', 'marker']
        args = _build_args(self.args, attrs)
        args['format'] = 'json' if getattr(self.args, 'detail') else 'text'
    
        try:    
            print_list(self.client.list_shared_by_others(**args))
        except Fault as err:
            raise CLIError(message=unicode(err), status=err.status, importance=err.status/100)
