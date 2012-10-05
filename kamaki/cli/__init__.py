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
from argparse import ArgumentParser, ArgumentError
from base64 import b64encode
from os.path import abspath, basename, exists
from sys import exit, stdout, stderr, argv

try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict

#from kamaki import clients
from .errors import CLIError, CLISyntaxError, CLICmdIncompleteError, CLICmdSpecError
from .config import Config #TO BE REMOVED
from .utils import bold, magenta, red, yellow, print_list, print_dict
from .command_tree import CommandTree
from argument import _arguments, parse_known_args

cmd_spec_locations = [
    'kamaki.cli.commands',
    'kamaki.commands',
    'kamaki.cli',
    'kamaki',
    '']
_commands = CommandTree(name='kamaki', description='A command line tool for poking clouds')

#If empty, all commands are loaded, if not empty, only commands in this list
#e.g. [store, lele, list, lolo] is good to load store_list but not list_store
#First arg should always refer to a group
candidate_command_terms = []
allow_no_commands = False
allow_all_commands = False
allow_subclass_signatures = False

def _allow_class_in_cmd_tree(cls):
    global allow_all_commands
    if allow_all_commands:
        return True
    global allow_no_commands 
    if allow_no_commands:
        return False

    term_list = cls.__name__.split('_')
    global candidate_command_terms
    index = 0
    for term in candidate_command_terms:
        try:
            index += 1 if term_list[index] == term else 0
        except IndexError: #Whole term list matched!
            return True
    if allow_subclass_signatures:
        if index == len(candidate_command_terms) and len(term_list) > index:
            try: #is subterm already in _commands?
                _commands.get_command('_'.join(term_list[:index+1]))
            except KeyError: #No, so it must be placed there
                return True
        return False

    return True if index == len(term_list) else False

def command():
    """Class decorator that registers a class as a CLI command"""

    def decorator(cls):
        """Any class with name of the form cmd1_cmd2_cmd3_... is accepted"""

        if not _allow_class_in_cmd_tree(cls):
            return cls

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

        #store each term, one by one, first
        _commands.add_command(cls.__name__, cls.description, cls)
        return cls
    return decorator

def _update_parser(parser, arguments):
    for name, argument in arguments.items():
        try:
            argument.update_parser(parser, name)
        except ArgumentError:
            pass

def _init_parser(exe):
    parser = ArgumentParser(add_help=False)
    parser.prog='%s <cmd_group> [<cmd_subbroup> ...] <cmd>'%exe
    _update_parser(parser, _arguments)
    return parser

def _print_error_message(cli_err):
    errmsg = unicode(cli_err) + (' (%s)'%cli_err.status if cli_err.status else ' ')
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
        print()

def get_command_group(unparsed):
    groups = _arguments['config'].get_groups()
    for grp_candidate in unparsed:
        if grp_candidate in groups:
            unparsed.remove(grp_candidate)
            return grp_candidate
    return None

def load_command(group, unparsed, reload_package=False):
    global candidate_command_terms
    candidate_command_terms = [group] + unparsed
    pkg = load_group_package(group, reload_package)

    #From all possible parsed commands, chose the first match in user string
    final_cmd = _commands.get_command(group)
    for term in unparsed:
        cmd = final_cmd.get_subcmd(term)
        if cmd is not None:
            final_cmd = cmd
            unparsed.remove(cmd.name)
    return final_cmd

def shallow_load():
    """Load only group names and descriptions"""
    global allow_no_commands 
    allow_no_commands = True#load only descriptions
    for grp in _arguments['config'].get_groups():
        load_group_package(grp)
    allow_no_commands = False

def load_group_package(group, reload_package=False):
    spec_pkg = _arguments['config'].value.get(group, 'cli')
    for location in cmd_spec_locations:
        location += spec_pkg if location == '' else ('.'+spec_pkg)
        try:
            package = __import__(location, fromlist=['API_DESCRIPTION'])
        except ImportError:
            continue
        if reload_package:
            reload(package)
        for grp, descr in package.API_DESCRIPTION.items():
            _commands.add_command(grp, descr)
        return package
    raise CLICmdSpecError(details='Cmd Spec Package %s load failed'%spec_pkg)

def print_commands(prefix=None, full_depth=False):
    cmd_list = _commands.get_groups() if prefix is None else _commands.get_subcommands(prefix)
    cmds = {}
    for subcmd in cmd_list:
        if subcmd.sublen() > 0:
            sublen_str = '( %s more terms ... )'%subcmd.sublen()
            cmds[subcmd.name] = [subcmd.help, sublen_str] if subcmd.has_description else subcmd_str
        else:
            cmds[subcmd.name] = subcmd.help
    if len(cmds) > 0:
        print('\nOptions:')
        print_dict(cmds, ident=12)
    if full_depth:
        _commands.pretty_print()

def one_command():
    _debug = False
    _help = False
    _verbose = False
    try:
        exe = basename(argv[0])
        parser = _init_parser(exe)
        parsed, unparsed = parse_known_args(parser)
        _debug = _arguments['debug'].value
        _help = _arguments['help'].value
        _verbose = _arguments['verbose'].value
        if _arguments['version'].value:
            exit(0)

        group = get_command_group(unparsed)
        if group is None:
            parser.print_help()
            shallow_load()
            print_commands(full_depth=_verbose)
            exit(0)

        cmd = load_command(group, unparsed)
        if _help or not cmd.is_command:
            if cmd.has_description:
                parser.description = cmd.help 
            else:
                try:
                    parser.description = _commands.get_closest_ancestor_command(cmd.path).help
                except KeyError:
                    parser.description = ' '
            parser.prog = '%s %s '%(exe, cmd.path.replace('_', ' '))
            if cmd.is_command:
                cli = cmd.get_class()
                parser.prog += cli.syntax
                _update_parser(parser, cli().arguments)
            else:
                parser.prog += '[...]'
            parser.print_help()

            #Shuuuut, we now have to load one more level just to see what is missing
            global allow_subclass_signatures 
            allow_subclass_signatures = True
            load_command(group, cmd.path.split('_')[1:], reload_package=True)

            print_commands(cmd.path, full_depth=_verbose)
            exit(0)

        cli = cmd.get_class()
        executable = cli(_arguments)
        _update_parser(parser, executable.arguments)
        parser.prog = '%s %s %s'%(exe, cmd.path.replace('_', ' '), cli.syntax)
        parse_known_args(parser)
        try:
            ret = executable.main(*unparsed)
            exit(ret)
        except TypeError as e:
            if e.args and e.args[0].startswith('main()'):
                parser.print_help()
                exit(1)
            else:
                raise
    except CLIError as err:
        if _debug:
            raise
        _print_error_message(err)
        exit(1)
