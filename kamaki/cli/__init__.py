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

from kamaki.cli.argument import ArgumentParseManager
from kamaki.cli.history import History
from kamaki.cli.utils import print_dict, red, magenta, yellow
from kamaki.cli.errors import CLIError

_help = False
_debug = False
_include = False
_verbose = False
_colors = False
kloger = None

#  command auxiliary methods

_best_match = []


def _arg2syntax(arg):
    return arg.replace(
        '____', '[:').replace(
            '___', ':').replace(
                '__', ']').replace(
                    '_', ' ')


def _construct_command_syntax(cls):
        spec = getargspec(cls.main.im_func)
        args = spec.args[1:]
        n = len(args) - len(spec.defaults or ())
        required = ' '.join(['<%s>' % _arg2syntax(x) for x in args[:n]])
        optional = ' '.join(['[%s]' % _arg2syntax(x) for x in args[n:]])
        cls.syntax = ' '.join(x for x in [required, optional] if x)
        if spec.varargs:
            cls.syntax += ' <%s ...>' % spec.varargs


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
    if not prefix:
        _best_match = []

    if num_of_matching_terms and len(_best_match) <= num_of_matching_terms:
        if len(_best_match) < num_of_matching_terms:
            _best_match = name_terms[:num_of_matching_terms]
        return True
    return False


def command(cmd_tree, prefix='', descedants_depth=1):
    """Load a class as a command
        e.g. spec_cmd0_cmd1 will be command spec cmd0

        :param cmd_tree: is initialized in cmd_spec file and is the structure
            where commands are loaded. Var name should be _commands
        :param prefix: if given, load only commands prefixed with prefix,
        :param descedants_depth: is the depth of the tree descedants of the
            prefix command. It is used ONLY if prefix and if prefix is not
            a terminal command

        :returns: the specified class object
    """

    def wrap(cls):
        global kloger
        cls_name = cls.__name__

        if not cmd_tree:
            if _debug:
                kloger.warning('command %s found but not loaded' % cls_name)
            return cls

        name_terms = cls_name.split('_')
        if not _update_best_match(name_terms, prefix):
            if _debug:
                kloger.warning('%s failed to update_best_match' % cls_name)
            return None

        global _best_match
        max_len = len(_best_match) + descedants_depth
        if len(name_terms) > max_len:
            partial = '_'.join(name_terms[:max_len])
            if not cmd_tree.has_command(partial):  # add partial path
                cmd_tree.add_command(partial)
            if _debug:
                kloger.warning('%s failed max_len test' % cls_name)
            return None

        (
            cls.description, sep, cls.long_description
        ) = cls.__doc__.partition('\n')
        _construct_command_syntax(cls)

        cmd_tree.add_command(cls_name, cls.description, cls)
        return cls
    return wrap


cmd_spec_locations = [
    'kamaki.cli.commands',
    'kamaki.commands',
    'kamaki.cli',
    'kamaki',
    '']


#  Generic init auxiliary functions


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
        return

    if debug:
        add_handler('requests', logging.INFO, prefix='* ')
        add_handler('clients.send', logging.DEBUG, prefix='> ')
        add_handler('clients.recv', logging.DEBUG, prefix='< ')
        add_handler('kamaki', logging.DEBUG, prefix='(debug): ')
    elif verbose:
        add_handler('requests', logging.INFO, prefix='* ')
        add_handler('clients.send', logging.INFO, prefix='> ')
        add_handler('clients.recv', logging.INFO, prefix='< ')
        add_handler('kamaki', logging.INFO, prefix='(i): ')
    if include:
        add_handler('data.send', logging.INFO, prefix='>[data]: ')
        add_handler('data.recv', logging.INFO, prefix='<[data]: ')
    add_handler('kamaki', logging.WARNING, prefix='(warning): ')
    global kloger
    kloger = logging.getLogger('kamaki')


def _init_session(arguments):
    global _help
    _help = arguments['help'].value
    global _debug
    _debug = arguments['debug'].value
    global _include
    _include = arguments['include'].value
    global _verbose
    _verbose = arguments['verbose'].value
    global _colors
    _colors = arguments['config'].get('global', 'colors')
    if not (stdout.isatty() and _colors == 'on'):
        from kamaki.cli.utils import remove_colors
        remove_colors()
    _silent = arguments['silent'].value
    _setup_logging(_silent, _debug, _verbose, _include)


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
    global kloger
    descriptions = {}
    for spec in arguments['config'].get_groups():
        pkg = _load_spec_module(spec, arguments, '_commands')
        if pkg:
            cmds = None
            try:
                _cnf = arguments['config']
                cmds = [cmd for cmd in getattr(pkg, '_commands') if _cnf.get(
                    cmd.name, 'cli')]
            except AttributeError:
                if _debug:
                    kloger.warning('No description for %s' % spec)
            try:
                for cmd in cmds:
                    descriptions[cmd.name] = cmd.description
            except TypeError:
                if _debug:
                    kloger.warning('no cmd specs in module %s' % spec)
        elif _debug:
            kloger.warning('Loading of %s cmd spec failed' % spec)
    print('\nOptions:\n - - - -')
    print_dict(descriptions)


def _load_all_commands(cmd_tree, arguments):
    _cnf = arguments['config']
    specs = [spec for spec in _cnf.get_groups() if _cnf.get(spec, 'cli')]
    for spec in specs:
        try:
            spec_module = _load_spec_module(spec, arguments, '_commands')
            spec_commands = getattr(spec_module, '_commands')
        except AttributeError:
            if _debug:
                global kloger
                kloger.warning('No valid description for %s' % spec)
            continue
        for spec_tree in spec_commands:
            if spec_tree.name == spec:
                cmd_tree.add_tree(spec_tree)
                break


#  Methods to be used by CLI implementations


def print_subcommands_help(cmd):
    printout = {}
    for subcmd in cmd.get_subcommands():
        spec, sep, print_path = subcmd.path.partition('_')
        printout[print_path.replace('_', ' ')] = subcmd.description
    if printout:
        print('\nOptions:\n - - - -')
        print_dict(printout)


def update_parser_help(parser, cmd):
    global _best_match
    parser.syntax = parser.syntax.split('<')[0]
    parser.syntax += ' '.join(_best_match)

    description = ''
    if cmd.is_command:
        cls = cmd.get_class()
        parser.syntax += ' ' + cls.syntax
        parser.update_arguments(cls().arguments)
        description = getattr(cls, 'long_description', '')
        description = description.strip()
    else:
        parser.syntax += ' <...>'
    if cmd.has_description:
        parser.parser.description = cmd.help + (
            ('\n%s' % description) if description else '')
    else:
        parser.parser.description = description


def print_error_message(cli_err):
    errmsg = '%s' % cli_err
    if cli_err.importance == 1:
        errmsg = magenta(errmsg)
    elif cli_err.importance == 2:
        errmsg = yellow(errmsg)
    elif cli_err.importance > 2:
        errmsg = red(errmsg)
    stdout.write(errmsg)
    for errmsg in cli_err.details:
        print('| %s' % errmsg)


def exec_cmd(instance, cmd_args, help_method):
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


def set_command_params(parameters):
    """Add a parameters list to a command

    :param paramters: (list of str) a list of parameters
    """
    global command
    def_params = list(command.func_defaults)
    def_params[0] = parameters
    command.func_defaults = tuple(def_params)


#  CLI Choice:

def run_one_cmd(exe_string, parser):
    global _history
    _history = History(
        parser.arguments['config'].get('history', 'file'))
    _history.add(' '.join([exe_string] + argv[1:]))
    from kamaki.cli import one_command
    one_command.run(parser, _help)


def run_shell(exe_string, parser):
    from command_shell import _init_shell
    shell = _init_shell(exe_string, parser)
    _load_all_commands(shell.cmd_tree, parser.arguments)
    shell.run(parser)


def main():
    try:
        exe = basename(argv[0])
        parser = ArgumentParseManager(exe)

        if parser.arguments['version'].value:
            exit(0)

        log_file = parser.arguments['config'].get('global', 'log_file')
        if log_file:
            from kamaki.logger import set_log_filename
            set_log_filename(log_file)

        _init_session(parser.arguments)

        from kamaki.cli.utils import suggest_missing
        suggest_missing()

        if parser.unparsed:
            run_one_cmd(exe, parser)
        elif _help:
            parser.parser.print_help()
            _groups_help(parser.arguments)
        else:
            run_shell(exe, parser)
    except CLIError as err:
        print_error_message(err)
        if _debug:
            raise err
        exit(1)
    except Exception as er:
        print('Unknown Error: %s' % er)
        if _debug:
            raise
        exit(1)
