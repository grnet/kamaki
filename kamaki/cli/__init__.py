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
candidate_command_terms = [None]

def command():
    """Class decorator that registers a class as a CLI command"""

    def decorator(cls):
        """Any class with name of the form cmd1_cmd2_cmd3_... is accepted"""
        term_list = cls.__name__.split('_')
        global candidate_command_terms

        tmp_tree = _commands
        if len(candidate_command_terms) > 0:
            #This is the case of a one-command execution: discard if not requested
            if term_list[0] != candidate_command_terms[0]:
                return cls
            i = 0
            for term in term_list:
                #check if the term is requested by used
                if term not in candidate_command_terms[i:]:
                    return cls
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

def load_command(group, unparsed):
    global candidate_command_terms
    candidate_command_terms = [group] + unparsed
    pkg = load_group_package(group)

    #From all possible parsed commands, chose one
    final_cmd = group
    next_names = [None]
    next_names = _commands.get_command_names(final_cmd)
    while len(next_names) > 0:
        if len(next_names) == 1:
            final_cmd+='_'+next_names[0]
        else:#choose the first in user string
            pos = unparsed.index(next_names[0])
            choice = 0
            for i, name in enumerate(next_names[1:]):
                tmp_index = unparsed.index(name)
                if tmp_index < pos:
                    pos = tmp_index
                    choice = i+1
            final_cmd+='_'+next_names[choice]
        next_names = _commands.get_command_names(final_cmd)
    cli = _commands.get_class(final_cmd)
    if cli is None:
        raise CLICmdIncompleteError(details='%s'%final_cmd)
    return cli


def load_group_descriptions(spec_pkg):
    for location in cmd_spec_locations:
        location += spec_pkg if location == '' else ('.'+spec_pkg)
        try:
            package = __import__(location, fromlist=['API_DESCRIPTION'])
        except ImportError:
            continue
        for grp, descr in package.API_DESCRIPTION.items():
            _commands.add_command(grp, descr)
        return package
    raise CLICmdSpecError(details='Cmd Spec Package %s load failed'%spec_pkg)

def shallow_load_groups():
    """Load only group names and descriptions"""
    for grp in _arguments['config'].get_groups():
        spec_pkg = _arguments['config'].value.get(grp, 'cli')
        load_group_descriptions(spec_pkg)

def load_group_package(group):
    spec_pkg = _arguments['config'].value.get(group, 'cli')
    for location in cmd_spec_locations:
        location += spec_pkg if location == '' else ('.'+spec_pkg)
        try:
            package = __import__(location)
        except ImportError:
            continue
        return package
    raise CLICmdSpecError(details='Cmd Spec Package %s load failed'%spec_pkg)

def print_commands(prefix=[]):
    grps = {}
    for grp in _commands.get_command_names(prefix):
        grps[grp] = _commands.get_description(grp)
    print_dict(grps, ident=12)

def one_command():
    _debug = False
    try:
        exe = basename(argv[0])
        parser = _init_parser(exe)
        parsed, unparsed = parse_known_args(parser)
        if _arguments['debug'].value:
            _debug = True
        if _arguments['version'].value:
            exit(0)

        group = get_command_group(unparsed)
        if group is None:
            parser.print_help()
            shallow_load_groups()
            print('\nCommand groups:')
            print_commands()
            exit(0)

        cli = load_command(group, unparsed)
        print('And this is how I get my command! YEAAAAAAH! %s'%cli)

    except CLIError as err:
        if _debug:
            raise
        _print_error_message(err)
        exit(1)
