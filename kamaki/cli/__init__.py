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
from .errors import CLIError, CLISyntaxError, CLICmdIncompleteError
from .config import Config #TO BE REMOVED
from .utils import bold, magenta, red, yellow, CommandTree, print_list, print_dict
from argument import _arguments, parse_known_args

cmd_spec_locations = [
    'kamaki.cli.commands',
    'kamaki.commands',
    'kamaki.cli',
    'kamaki',
    '']
_commands = CommandTree(description='A command line tool for poking clouds')

#If empty, all commands are loaded, if not empty, only commands in this list
#e.g. [store, lele, list, lolo] is good to load store_list but not list_store
#First arg should always refer to a group
candidate_command_terms = []
do_no_load_commands = False
put_subclass_signatures_in_commands = False

def _put_subclass_signatures_in_commands(cls):
    global candidate_command_terms

    part_name = '_'.join(candidate_command_terms)
    try:
        empty, same, rest = cls.__name__.partition(part_name)
    except ValueError:
        return False
    if len(empty) != 0:
        return False
    if len(rest) == 0:
        _commands.add_path(cls.__name__, (cls.__doc__.partition('\n'))[0])
    else:
        rest_terms = rest[1:].split('_')
        new_name = part_name+'_'+rest_terms[0]
        desc = cls.__doc__.partition('\n')[0] if new_name == cls.__name__ else ''
        _commands.add_path(new_name, desc)
    return True


def _put_class_path_in_commands(cls):
    #Maybe I should apologise for the globals, but they are used in a smart way, so...
    global candidate_command_terms
    term_list = cls.__name__.split('_')

    tmp_tree = _commands
    if len(candidate_command_terms) > 0:
        #This is the case of a one-command execution: discard if not requested
        if term_list[0] != candidate_command_terms[0]:
            return False
        i = 0
        for term in term_list:
            #check if the term is requested by user
            if term not in candidate_command_terms[i:]:
                return False
            i = 1+candidate_command_terms.index(term)
            #now, put the term in the tree
            if term not in tmp_tree.get_command_names():
                tmp_tree.add_command(term)
            tmp_tree = tmp_tree.get_command(term)
    else:
        #Just insert everything in the tree
        for term in term_list:
            if term not in tmp_tree.get_command_names():
                tmp_tree.add_command(term)
            tmp_tree = tmp_tree.get_command()
    return True

def command():
    """Class decorator that registers a class as a CLI command"""

    def decorator(cls):
        """Any class with name of the form cmd1_cmd2_cmd3_... is accepted"""
        global do_no_load_commands
        if do_no_load_commands:
            return cls

        global put_subclass_signatures_in_commands
        if put_subclass_signatures_in_commands:
            _put_subclass_signatures_in_commands(cls)
            return cls

        if not _put_class_path_in_commands(cls):
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
        argument.update_parser(parser, name)

def _init_parser(exe):
    parser = ArgumentParser(add_help=False)
    parser.prog='%s <cmd_group> [<cmd_subbroup> ...] <cmd>'%exe
    _update_parser(parser, _arguments)
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

def _expand_cmd(cmd_prefix, unparsed):
    if len(unparsed) == 0:
        return None
    prefix = (cmd_prefix+'_') if len(cmd_prefix) > 0 else ''
    for term in _commands.list(cmd_prefix):
        try:
            unparsed.remove(term)
        except ValueError:
            continue
        return prefix+term
    return None

def _retrieve_cmd(unparsed):
    cmd_str = None
    cur_cmd = _expand_cmd('', unparsed)
    while cur_cmd is not None:
        cmd_str = cur_cmd
        cur_cmd = _expand_cmd(cur_cmd, unparsed)
    if cmd_str is None:
        print(bold('Command groups:'))
        print_list(_commands.get_groups(), ident=14)
        print
        return None
    try:
        return _commands.get_class(cmd_str)
    except CLICmdIncompleteError:
        print(bold('%s:'%cmd_str))
        print_list(_commands.list(cmd_str))
    return None

def get_command_group(unparsed):
    groups = _arguments['config'].get_groups()
    for grp_candidate in unparsed:
        if grp_candidate in groups:
            unparsed.remove(grp_candidate)
            return grp_candidate
    return None

def _order_in_list(list1, list2):
    order = 0
    for i,term in enumerate(list1):
        order += len(list2)*i*list2.index(term)
    return order

def load_command(group, unparsed, reload_package=False):
    global candidate_command_terms
    candidate_command_terms = [group] + unparsed
    pkg = load_group_package(group, reload_package)

    #From all possible parsed commands, chose one
    final_cmd = group
    next_names = [None]
    next_names = _commands.get_command_names(final_cmd)
    while len(next_names) > 0:
        if len(next_names) == 1:
            final_cmd+='_'+next_names[0]
        else:#choose the first in user string
            try:
                pos = unparsed.index(next_names[0])
            except ValueError:
                return final_cmd
            choice = 0
            for i, name in enumerate(next_names[1:]):
                tmp_index = unparsed.index(name)
                if tmp_index < pos:
                    pos = tmp_index
                    choice = i+1
            final_cmd+='_'+next_names[choice]
        next_names = _commands.get_command_names(final_cmd)
    return final_cmd

def shallow_load():
    """Load only group names and descriptions"""
    global do_no_load_commands
    do_no_load_commands = True#load only descriptions
    for grp in _arguments['config'].get_groups():
        load_group_package(grp)
    do_no_load_commands = False

def load_group_package(group, reload_package=False):
    spec_pkg = _arguments['config'].value.get(group, 'cli')
    for location in cmd_spec_locations:
        location += spec_pkg if location == '' else ('.'+spec_pkg)
        try:
            package = __import__(location, fromlist=['API_DESCRIPTION'])
            if reload_package:
                reload(package)
        except ImportError:
            continue
        for grp, descr in package.API_DESCRIPTION.items():
            _commands.add_command(grp, descr)
        return package
    raise CLICmdSpecError(details='Cmd Spec Package %s load failed'%spec_pkg)

def print_commands(prefix=[], full_tree=False):
    cmd = _commands.get_command(prefix)
    grps = {' . ':cmd.description} if cmd.is_command else {}
    for grp in cmd.get_command_names():
        grps[grp] = cmd.get_description(grp)
    print('\nOptions:')
    print_dict(grps, ident=12)
    if full_tree:
        _commands.print_tree(level=-1)

def one_command():
    _debug = False
    _help = False
    try:
        exe = basename(argv[0])
        parser = _init_parser(exe)
        parsed, unparsed = parse_known_args(parser)
        _debug = _arguments['debug'].value
        _help = _arguments['help'].value
        if _arguments['version'].value:
            exit(0)

        group = get_command_group(unparsed)
        if group is None:
            parser.print_help()
            shallow_load()
            print_commands(full_tree=_arguments['verbose'].value)
            print()
            exit(0)

        command_path = load_command(group, unparsed)
        cli = _commands.get_class(command_path)
        if cli is None or _help: #Not a complete command
            parser.description = _commands.closest_description(command_path)
            parser.prog = '%s '%exe
            for term in command_path.split('_'):
                parser.prog += '%s '%term
            if cli is None:
                parser.prog += '<...>'
            else:
                print(unicode(cli().syntax))
                parser.prog += cli.syntax
                _update_parser(parser, cli().arguments)
            parser.print_help()

            #Shuuuut, we now have to load one more level just to see what is missing
            global put_subclass_signatures_in_commands
            put_subclass_signatures_in_commands = True
            load_command(group, command_path.split('_')[1:], reload_package=True)

            print_commands(command_path, full_tree=_arguments['verbose'].value)
            exit(0)

        #Now, load the cmd
        cmd = cli(_arguments)
        parser = _init_parser(cmd.arguments)
        parsed, unparsed = parse_known_args(parser)
        for term in command_path.split('_'):
            unparsed.remove(term)
        try:
            ret = cmd.main(*unparsed)
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
