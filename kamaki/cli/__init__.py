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

from __future__ import print_function

import gevent.monkey
#Monkey-patch everything for gevent early on
gevent.monkey.patch_all()

import logging

from inspect import getargspec
from argparse import ArgumentParser
from base64 import b64encode
from os.path import abspath, basename, exists
from sys import exit, stdout, stderr, argv

try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict

#from kamaki import clients
from .errors import CLIError
from .config import Config #TO BE REMOVED
from .utils import magenta, red, yellow, CommandTree
from argument import _arguments, parse_known_args

_commands = CommandTree()

GROUPS={}
CLI_LOCATIONS = ['kamaki.cli.commands', 'kamaki.commands', 'kamaki.cli', 'kamaki', '']

def command():
    """Class decorator that registers a class as a CLI command"""

    def decorator(cls):
        """Any class with name of the form cmd1_cmd2_cmd3_... is accepted"""
        cls.description, sep, cls.long_description = cls.__doc__.partition('\n')

        # Generate a syntax string based on main's arguments
        spec = getargspec(cls.main.im_func)
        args = spec.args[1:]
        n = len(args) - len(spec.defaults or ())
        required = ' '.join('<%s>' % x.replace('____', '[:').replace('___', ':').replace('__',']').\
            replace('_', ' ') for x in args[:n])
        optional = ' '.join('[%s]' % x.replace('____', '[:').replace('___', ':').replace('__', ']').\
            replace('_', ' ') for x in args[n:])
        cls.syntax = ' '.join(x for x in [required, optional] if x)
        if spec.varargs:
            cls.syntax += ' <%s ...>' % spec.varargs

        _commands.add(cls.__name__, cls)
        return cls
    return decorator

def set_api_description(api, description):
    """Method to be called by api CLIs
    Each CLI can set more than one api descriptions"""
    GROUPS[api] = description

def _init_parser(exe):
    parser = ArgumentParser(add_help=True)
    parser.prog='%s <cmd_group> [<cmd_subbroup> ...] <cmd>'%exe
    for name, argument in _arguments.items():
        argument.update_parser(parser, name)
    return parser

def _print_error_message(cli_err):
    errmsg = '%s'%unicode(cli_err) +' (%s)'%cli_err.status if cli_err.status else ' '
    if cli_err.importance == 1:
        errmsg = magenta(errmsg)
    elif cli_err.importance == 2:
        errmsg = yellow(errmsg)
    elif cli_err.importance > 2:
        errmsg = red(errmsg)
    stdout.write(errmsg)
    if cli_err.details is not None and len(cli_err.details) > 0:
        print(': %s'%cli_err.details)
    else:
        print

def one_command():
    try:
        exe = basename(argv[0])
        parser = _init_parser(exe)
        parsed, unparsed = parse_known_args(parser)
        if _arguments['version'].value:
            exit(0)
    except CLIError as err:
        _print_error_message(err)
        exit(1)
