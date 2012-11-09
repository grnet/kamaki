# Copyright 2012-2013 GRNET S.A. All rights reserved.
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

from sys import argv
from os.path import basename
from kamaki.cli.argument import _arguments, parse_known_args, init_parser
from kamaki.cli.history import History
from kamaki.cli.utils import print_dict

_help = False
_debug = False
_verbose = False
_colors = False

cmd_spec_locations = [
    'kamaki.cli.commands',
    'kamaki.commands',
    'kamaki.cli',
    'kamaki',
    '']


def _init_session(arguments):
    global _help
    _help = arguments['help'].value
    global _debug
    _debug = arguments['debug'].value
    global _verbose
    _verbose = arguments['verbose'].value
    global _colors
    _colors = arguments['config'].get('global', 'colors')


def get_command_group(unparsed, arguments):
    groups = arguments['config'].get_groups()
    for grp_candidate in unparsed:
        if grp_candidate in groups:
            unparsed.remove(grp_candidate)
            return grp_candidate
    return None


def _load_spec_module(spec, arguments, module):
    spec_name = arguments['config'].get(spec, 'cli')
    pkg = None
    if spec_name is None:
        spec_name = '%s_cli' % spec
    for location in cmd_spec_locations:
        location += spec_name if location == '' else '.%s' % spec_name
        try:
            pkg = __import__(location, fromlist=[module])
        except ImportError:
            continue
    return pkg


def _groups_help(arguments):
    global _debug
    descriptions = {}
    for spec in arguments['config'].get_groups():
        pkg = _load_spec_module(spec, arguments, '_commands')
        if pkg:
            cmds = None
            try:
                cmds = getattr(pkg, '_commands')
            except AttributeError:
                if _debug:
                    print('Warning: No description for %s' % spec)
            try:
                for cmd in cmds:
                    descriptions[cmd.name] = cmd.description
            except TypeError:
                if _debug:
                    print('Warning: no cmd specs in module %s' % spec)
        elif _debug:
            print('Warning: Loading of %s cmd spec failed' % spec)
    print('\nOptions:\n - - - -')
    print_dict(descriptions)


def one_cmd(parser, unparsed, arguments):
    group = get_command_group(unparsed, arguments)
    if not group:
        parser.print_help()
        _groups_help(arguments)


def interactive_shell():
    print('INTERACTIVE SHELL')


def main():
    exe = basename(argv[0])
    parser = init_parser(exe, _arguments)
    parsed, unparsed = parse_known_args(parser, _arguments)
    print('PARSED: %s\nUNPARSED: %s' % parsed, unparsed)

    if _arguments['version'].value:
        exit(0)

    _init_session(_arguments)

    if unparsed:
        _history = History(_arguments['config'].get('history', 'file'))
        _history.add(' '.join([exe] + argv[1:]))
        one_cmd(parser, unparsed, _arguments)
    elif _help:
        parser.print_help()
    else:
        interactive_shell()
