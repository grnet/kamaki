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

import inspect
import logging
import sys

from argparse import ArgumentParser
from base64 import b64encode
from os.path import abspath, basename, exists
from sys import exit, stdout, stderr

try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict

from colors import magenta, red, yellow
#from progress.bar import IncrementalBar
#from requests.exceptions import ConnectionError

from . import clients
from .config import Config
#from .utils import print_list, print_dict, print_items, format_size

_commands = OrderedDict()

GROUPS = {}
CLI_LOCATIONS = ['', 'kamaki', 'kamaki.clients', 'kamaki.clis']

class CLIError(Exception):
    def __init__(self, message, status=0, details='', importance=0):
        """importance is set by the raiser
        0 is the lowest possible importance
        Suggested values: 0, 1, 2, 3
        """
        super(CLIError, self).__init__(message, status, details)
        self.message = message
        self.status = status
        self.details = details
        self.importance = importance

def command(group=None, name=None, syntax=None):
    """Class decorator that registers a class as a CLI command."""

    def decorator(cls):
        grp, sep, cmd = cls.__name__.partition('_')
        if not sep:
            grp, cmd = None, cls.__name__

        #cls.api = api
        cls.group = group or grp
        cls.name = name or cmd

        short_description, sep, long_description = cls.__doc__.partition('\n')
        cls.description = short_description
        cls.long_description = long_description or short_description

        cls.syntax = syntax
        if cls.syntax is None:
            # Generate a syntax string based on main's arguments
            spec = inspect.getargspec(cls.main.im_func)
            args = spec.args[1:]
            n = len(args) - len(spec.defaults or ())
            required = ' '.join('<%s>' % x.replace('____', '[:').replace('___', ':').replace('__',']').replace('_', ' ') for x in args[:n])
            optional = ' '.join('[%s]' % x.replace('____', '[:').replace('___', ':').replace('__', ']').replace('_', ' ') for x in args[n:])
            cls.syntax = ' '.join(x for x in [required, optional] if x)
            if spec.varargs:
                cls.syntax += ' <%s ...>' % spec.varargs

        if cls.group not in _commands:
            _commands[cls.group] = OrderedDict()
        _commands[cls.group][cls.name] = cls
        return cls
    return decorator

def set_api_description(api, description):
    """Method to be called by api CLIs
    Each CLI can set more than one api descriptions"""
    GROUPS[api] = description

def main():

    def print_groups():
        print('\nGroups:')
        for group in _commands:
            description = GROUPS.get(group, '')
            print(' ', group.ljust(12), description)

    def print_commands(group):
        description = GROUPS.get(group, '')
        if description:
            print('\n' + description)

        print('\nCommands:')
        for name, cls in _commands[group].items():
            print(' ', name.ljust(14), cls.description)

    def manage_logging_handlers(args):
        """This is mostly to handle logging for clients package"""

        def add_handler(name, level, prefix=''):
            h = logging.StreamHandler()
            fmt = logging.Formatter(prefix + '%(message)s')
            h.setFormatter(fmt)
            logger = logging.getLogger(name)
            logger.addHandler(h)
            logger.setLevel(level)

        if args.silent:
            add_handler('', logging.CRITICAL)
        elif args.debug:
            add_handler('requests', logging.INFO, prefix='* ')
            add_handler('clients.send', logging.DEBUG, prefix='> ')
            add_handler('clients.recv', logging.DEBUG, prefix='< ')
        elif args.verbose:
            add_handler('requests', logging.INFO, prefix='* ')
            add_handler('clients.send', logging.INFO, prefix='> ')
            add_handler('clients.recv', logging.INFO, prefix='< ')
        elif args.include:
            add_handler('clients.recv', logging.INFO)
        else:
            add_handler('', logging.WARNING)

    def load_groups(config):
        """load groups and import CLIs and Modules"""
        #apis = set(['config']+config.apis())
        loaded_modules = {}
        for api in config.apis():
            api_cli = config.get(api, 'cli')
            if None == api_cli or len(api_cli)==0:
                print('Warnig: No Command Line Interface "%s" given for API "%s"'%(api_cli, api))
                print('\t(cli option in config file)')
                continue
            if not loaded_modules.has_key(api_cli):
                loaded_modules[api_cli] = False
                for location in CLI_LOCATIONS:
                    location += api_cli if location == '' else '.%s'%api_cli
                    try:
                        __import__(location)
                        loaded_modules[api_cli] = True
                        break
                    except ImportError:
                        pass
                if not loaded_modules[api_cli]:
                    print('Warning: failed to load Command Line Interface "%s" for API "%s"'%(api_cli, api))
                    print('\t(No suitable cli in known paths)')
                    continue
            if not GROUPS.has_key(api):
                GROUPS[api] = 'No description (interface: %s)'%api_cli

    def init_parser(exe):
        parser = ArgumentParser(add_help=False)
        parser.prog = '%s <group> <command>' % exe
        parser.add_argument('-h', '--help', dest='help', action='store_true',
                          default=False,
                          help="Show this help message and exit")
        parser.add_argument('--config', dest='config', metavar='PATH',
                          help="Specify the path to the configuration file")
        parser.add_argument('-d', '--debug', dest='debug', action='store_true',
                          default=False,
                          help="Include debug output")
        parser.add_argument('-i', '--include', dest='include', action='store_true',
                          default=False,
                          help="Include protocol headers in the output")
        parser.add_argument('-s', '--silent', dest='silent', action='store_true',
                          default=False,
                          help="Silent mode, don't output anything")
        parser.add_argument('-v', '--verbose', dest='verbose', action='store_true',
                          default=False,
                          help="Make the operation more talkative")
        parser.add_argument('-V', '--version', dest='version', action='store_true',
                          default=False,
                          help="Show version number and quit")
        parser.add_argument('-o', dest='options', action='append',
                          default=[], metavar="KEY=VAL",
                          help="Override a config value")
        return parser

    def find_term_in_args(arg_list, term_list):
        arg_tail = []
        while len(arg_list) > 0:
            group = arg_list.pop(0)
            if group.startswith('-') or group not in term_list:
                arg_tail.append(group)
            else:
                arg_list += arg_tail
                return group
        return None

    """Main Code"""
    exe = basename(sys.argv[0])
    parser = init_parser(exe)
    args, argv = parser.parse_known_args()

    #print version
    if args.version:
        import kamaki
        print("kamaki %s" % kamaki.__version__)
        exit(0)

    config = Config(args.config) if args.config else Config()

    #load config options from command line
    for option in args.options:
        keypath, sep, val = option.partition('=')
        if not sep:
            print("Invalid option '%s'" % option)
            exit(1)
        section, sep, key = keypath.partition('.')
        if not sep:
            print("Invalid option '%s'" % option)
            exit(1)
        config.override(section.strip(), key.strip(), val.strip())

    load_groups(config)
    group = find_term_in_args(argv, _commands)
    if not group:
        parser.print_help()
        print_groups()
        exit(1)

    parser.prog = '%s %s <command>' % (exe, group)
    command = find_term_in_args(argv, _commands[group])

    if not command:
        parser.print_help()
        print_commands(group)
        exit(0)

    cmd = _commands[group][command]()

    parser.prog = '%s %s %s' % (exe, group, command)
    if cmd.syntax:
        parser.prog += '  %s' % cmd.syntax
    parser.description = cmd.description
    parser.epilog = ''
    if hasattr(cmd, 'update_parser'):
        cmd.update_parser(parser)

    #check other args
    args, argv = parser.parse_known_args()

    if args.help:
        parser.print_help()
        exit(0)

    manage_logging_handlers(args)
    cmd.args = args
    cmd.config = config
    try:
        ret = cmd.main(*argv[2:])
        exit(ret)
    except TypeError as e:
        if e.args and e.args[0].startswith('main()'):
            parser.print_help()
            exit(1)
        else:
            raise
    except CLIError as err:
        errmsg = 'CLI Error '
        errmsg += '(%s): '%err.status if err.status else ': '
        errmsg += err.message if err.message else ''
        if err.importance == 1:
            errmsg = yellow(errmsg)
        elif err.importance == 2:
            errmsg = magenta(errmsg)
        elif err.importance > 2:
            errmsg = red(errmsg)
        print(errmsg, file=stderr)
        exit(1)

if __name__ == '__main__':
    main()
