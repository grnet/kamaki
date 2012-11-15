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

import logging
from sys import argv, exit, stdout
from os.path import basename
from inspect import getargspec

from kamaki.cli.argument import _arguments, parse_known_args, init_parser,\
    update_arguments
from kamaki.cli.history import History
from kamaki.cli.utils import print_dict, print_list, red, magenta, yellow
from kamaki.cli.errors import CLIError

_help = False
_debug = False
_verbose = False
_colors = False


def _construct_command_syntax(cls):
        spec = getargspec(cls.main.im_func)
        args = spec.args[1:]
        n = len(args) - len(spec.defaults or ())
        required = ' '.join('<%s>' % x\
            .replace('____', '[:')\
            .replace('___', ':')\
            .replace('__', ']').\
            replace('_', ' ') for x in args[:n])
        optional = ' '.join('[%s]' % x\
            .replace('____', '[:')\
            .replace('___', ':')\
            .replace('__', ']').\
            replace('_', ' ') for x in args[n:])
        cls.syntax = ' '.join(x for x in [required, optional] if x)
        if spec.varargs:
            cls.syntax += ' <%s ...>' % spec.varargs


def _get_cmd_tree_from_spec(spec, cmd_tree_list):
    for tree in cmd_tree_list:
        if tree.name == spec:
            return tree
    return None


_best_match = []


def _num_of_matching_terms(basic_list, attack_list):
    if not attack_list:
        return len(basic_list)

    matching_terms = 0
    for i, term in enumerate(basic_list):
        try:
            if term != attack_list[i]:
                break
        except IndexError:
            break
        matching_terms += 1
    return matching_terms


def _update_best_match(name_terms, prefix=[]):
    if prefix:
        pref_list = prefix if isinstance(prefix, list) else prefix.split('_')
    else:
        pref_list = []

    num_of_matching_terms = _num_of_matching_terms(name_terms, pref_list)
    global _best_match

    if num_of_matching_terms and len(_best_match) <= num_of_matching_terms:
        if len(_best_match) < num_of_matching_terms:
            _best_match = name_terms[:num_of_matching_terms]
        return True
    return False


def command(cmd_tree, prefix='', descedants_depth=1):
    """Load a class as a command
        spec_cmd0_cmd1 will be command spec cmd0
        @cmd_tree is initialized in cmd_spec file and is the structure
            where commands are loaded. Var name should be _commands
        @param prefix if given, load only commands prefixed with prefix,
        @param descedants_depth is the depth of the tree descedants of the
            prefix command. It is used ONLY if prefix and if prefix is not
            a terminal command
    """

    def wrap(cls):
        cls_name = cls.__name__

        if not cmd_tree:
            if _debug:
                print('Warning: command %s found but not loaded' % cls_name)
            return cls

        name_terms = cls_name.split('_')
        if not _update_best_match(name_terms, prefix):
            return None

        global _best_match
        max_len = len(_best_match) + descedants_depth
        if len(name_terms) > max_len:
            partial = '_'.join(name_terms[:max_len])
            if not cmd_tree.has_command(partial):  # add partial path
                cmd_tree.add_command(partial)
            return None

        cls.description, sep, cls.long_description\
        = cls.__doc__.partition('\n')
        _construct_command_syntax(cls)

        cmd_tree.add_command(cls_name, cls.description, cls)
        return cls
    return wrap


def get_cmd_terms():
    global command
    return [term for term in command.func_defaults[0]\
        if not term.startswith('-')]

cmd_spec_locations = [
    'kamaki.cli.commands',
    'kamaki.commands',
    'kamaki.cli',
    'kamaki',
    '']


def _setup_logging(silent=False, debug=False, verbose=False, include=False):
    """handle logging for clients package"""

    def add_handler(name, level, prefix=''):
        h = logging.StreamHandler()
        fmt = logging.Formatter(prefix + '%(message)s')
        h.setFormatter(fmt)
        logger = logging.getLogger(name)
        logger.addHandler(h)
        logger.setLevel(level)

    if silent:
        add_handler('', logging.CRITICAL)
    elif debug:
        add_handler('requests', logging.INFO, prefix='* ')
        add_handler('clients.send', logging.DEBUG, prefix='> ')
        add_handler('clients.recv', logging.DEBUG, prefix='< ')
    elif verbose:
        add_handler('requests', logging.INFO, prefix='* ')
        add_handler('clients.send', logging.INFO, prefix='> ')
        add_handler('clients.recv', logging.INFO, prefix='< ')
    elif include:
        add_handler('clients.recv', logging.INFO)
    else:
        add_handler('', logging.WARNING)


def _init_session(arguments):
    global _help
    _help = arguments['help'].value
    global _debug
    _debug = arguments['debug'].value
    global _verbose
    _verbose = arguments['verbose'].value
    global _colors
    _colors = arguments['config'].get('global', 'colors')
    if not (stdout.isatty() and _colors == 'on'):
        from kamaki.cli.utils import remove_colors
        remove_colors()
    _silent = arguments['silent'].value
    _include = arguments['include'].value
    _setup_logging(_silent, _debug, _verbose, _include)


def get_command_group(unparsed, arguments):
    groups = arguments['config'].get_groups()
    for term in unparsed:
        if term.startswith('-'):
            continue
        if term in groups:
            unparsed.remove(term)
            return term
        return None
    return None


def _load_spec_module(spec, arguments, module):
    spec_name = arguments['config'].get(spec, 'cli')
    if spec_name is None:
        return None
    pkg = None
    for location in cmd_spec_locations:
        location += spec_name if location == '' else '.%s' % spec_name
        try:
            pkg = __import__(location, fromlist=[module])
            return pkg
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
                cmds = [
                    cmd for cmd in getattr(pkg, '_commands')\
                    if arguments['config'].get(cmd.name, 'cli')
                ]
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


def _print_subcommands_help(cmd):
    printout = {}
    for subcmd in cmd.get_subcommands():
        spec, sep, print_path = subcmd.path.partition('_')
        printout[print_path.replace('_', ' ')] = subcmd.description
    if printout:
        print('\nOptions:\n - - - -')
        print_dict(printout)


def _update_parser_help(parser, cmd):
    global _best_match
    parser.prog = parser.prog.split('<')[0]
    parser.prog += ' '.join(_best_match)

    if cmd.is_command:
        cls = cmd.get_class()
        parser.prog += ' ' + cls.syntax
        arguments = cls().arguments
        update_arguments(parser, arguments)
    else:
        parser.prog += ' <...>'
    if cmd.has_description:
        parser.description = cmd.help


def _print_error_message(cli_err):
    errmsg = '%s' % cli_err
    if cli_err.importance == 1:
        errmsg = magenta(errmsg)
    elif cli_err.importance == 2:
        errmsg = yellow(errmsg)
    elif cli_err.importance > 2:
        errmsg = red(errmsg)
    stdout.write(errmsg)
    print_list(cli_err.details)


def _get_best_match_from_cmd_tree(cmd_tree, unparsed):
    matched = [term for term in unparsed if not term.startswith('-')]
    while matched:
        try:
            return cmd_tree.get_command('_'.join(matched))
        except KeyError:
            matched = matched[:-1]
    return None


def _exec_cmd(instance, cmd_args, help_method):
    try:
        return instance.main(*cmd_args)
    except TypeError as err:
        if err.args and err.args[0].startswith('main()'):
            print(magenta('Syntax error'))
            if _debug:
                raise err
            if _verbose:
                print(unicode(err))
            help_method()
        else:
            raise
    return 1


def set_command_param(param, value):
    if param == 'prefix':
        pos = 0
    elif param == 'descedants_depth':
        pos = 1
    else:
        return
    global command
    def_params = list(command.func_defaults)
    def_params[pos] = value
    command.func_defaults = tuple(def_params)


def one_cmd(parser, unparsed, arguments):
    group = get_command_group(list(unparsed), arguments)
    if not group:
        parser.print_help()
        _groups_help(arguments)
        exit(0)

    set_command_param(
        'prefix',
        [term for term in unparsed if not term.startswith('-')]
    )
    global _best_match
    _best_match = []

    spec_module = _load_spec_module(group, arguments, '_commands')

    cmd_tree = _get_cmd_tree_from_spec(group, spec_module._commands)

    if _best_match:
        cmd = cmd_tree.get_command('_'.join(_best_match))
    else:
        cmd = _get_best_match_from_cmd_tree(cmd_tree, unparsed)
        _best_match = cmd.path.split('_')
    if cmd is None:
        if _debug or _verbose:
            print('Unexpected error: failed to load command')
        exit(1)

    _update_parser_help(parser, cmd)

    if _help or not cmd.is_command:
        parser.print_help()
        _print_subcommands_help(cmd)
        exit(0)

    cls = cmd.get_class()
    executable = cls(arguments)
    parsed, unparsed = parse_known_args(parser, executable.arguments)
    for term in _best_match:
        unparsed.remove(term)
    _exec_cmd(executable, unparsed, parser.print_help)


def run_shell(exe_string, arguments):
    from command_shell import _init_shell
    shell = _init_shell(exe_string, arguments)
    #  Load all commands in shell CommandTree
    _config = arguments['config']
    for spec in [spec for spec in _config.get_groups()\
            if _config.get(spec, 'cli')]:
        try:
            spec_module = _load_spec_module(spec, arguments, '_commands')
            spec_commands = getattr(spec_module, '_commands')
        except AttributeError:
            if _debug:
                print('Warning: No valid description for %s' % spec)
            continue
        for spec_tree in spec_commands:
            if spec_tree.name == spec:
                shell.cmd_tree.add_tree(spec_tree)
                break
    shell.run()


def main():
    try:
        exe = basename(argv[0])
        parser = init_parser(exe, _arguments)
        parsed, unparsed = parse_known_args(parser, _arguments)

        if _arguments['version'].value:
            exit(0)

        _init_session(_arguments)

        if unparsed:
            _history = History(_arguments['config'].get('history', 'file'))
            _history.add(' '.join([exe] + argv[1:]))
            one_cmd(parser, unparsed, _arguments)
        elif _help:
            parser.print_help()
            _groups_help(_arguments)
        else:
            run_shell(exe, _arguments)
    except CLIError as err:
        if _debug:
            raise err
        _print_error_message(err)
        exit(1)
    except Exception as err:
        if _debug:
            raise err
        print('Unknown Error: %s' % err)
