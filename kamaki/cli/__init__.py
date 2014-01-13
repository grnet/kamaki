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
from sys import argv, exit, stdout, stderr
from os.path import basename, exists
from inspect import getargspec

from kamaki.cli.argument import ArgumentParseManager
from kamaki.cli.history import History
from kamaki.cli.utils import print_dict, red, magenta, yellow
from kamaki.cli.errors import CLIError, CLICmdSpecError
from kamaki.cli import logger
from kamaki.clients.astakos import CachedAstakosClient
from kamaki.clients import ClientError

_help = False
_debug = False
_verbose = False
_colors = False
kloger = None
filelog = None

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
        cls.syntax = ' '.join([required, optional])
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
        e.g., spec_cmd0_cmd1 will be command spec cmd0

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

        try:
            (
                cls.description, sep, cls.long_description
            ) = cls.__doc__.partition('\n')
        except AttributeError:
            raise CLICmdSpecError(
                'No commend in %s (acts as cmd description)' % cls.__name__)
        _construct_command_syntax(cls)

        cmd_tree.add_command(
            cls_name, cls.description, cls, cls.long_description)
        return cls
    return wrap


cmd_spec_locations = [
    'kamaki.cli.commands',
    'kamaki.commands',
    'kamaki.cli',
    'kamaki',
    '']


#  Generic init auxiliary functions


def _setup_logging(silent=False, debug=False, verbose=False):
    """handle logging for clients package"""

    if silent:
        logger.add_stream_logger(__name__, logging.CRITICAL)
        return

    sfmt, rfmt = '> %(message)s', '< %(message)s'
    if debug:
        print('Logging location: %s' % logger.get_log_filename())
        logger.add_stream_logger('kamaki.clients.send', logging.DEBUG, sfmt)
        logger.add_stream_logger('kamaki.clients.recv', logging.DEBUG, rfmt)
        logger.add_stream_logger(__name__, logging.DEBUG)
    elif verbose:
        logger.add_stream_logger('kamaki.clients.send', logging.INFO, sfmt)
        logger.add_stream_logger('kamaki.clients.recv', logging.INFO, rfmt)
        logger.add_stream_logger(__name__, logging.INFO)
    logger.add_stream_logger(__name__, logging.WARNING)
    global kloger
    kloger = logger.get_logger(__name__)


def _check_config_version(cnf):
    guess = cnf.guess_version()
    if exists(cnf.path) and guess < 0.12:
        print('Config file format version >= 0.12 is required (%s found)' % (
            guess))
        print('Configuration file: %s' % cnf.path)
        print('Attempting to fix this:')
        print('Calculating changes while preserving information')
        lost_terms = cnf.rescue_old_file()
        print('... DONE')
        if lost_terms:
            print 'The following information will NOT be preserved:'
            print '\t', '\n\t'.join(lost_terms)
        print('Kamaki is ready to convert the config file')
        stdout.write('Create (overwrite) file %s ? [y/N] ' % cnf.path)
        from sys import stdin
        reply = stdin.readline()
        if reply in ('Y\n', 'y\n'):
            cnf.write()
            print('... DONE')
        else:
            print('... ABORTING')
            raise CLIError(
                'Invalid format for config file %s' % cnf.path,
                importance=3, details=[
                    'Please, update config file',
                    'For automatic conversion, rerun and say Y'])


def _init_session(arguments, is_non_API=False):
    """
    :returns: cloud name
    """
    global _help
    _help = arguments['help'].value
    global _debug
    _debug = arguments['debug'].value
    global _verbose
    _verbose = arguments['verbose'].value
    _cnf = arguments['config']

    _silent = arguments['silent'].value
    _setup_logging(_silent, _debug, _verbose)

    if _help or is_non_API:
        return None

    _check_config_version(_cnf.value)

    global _colors
    _colors = _cnf.value.get('global', 'colors')
    if not (stdout.isatty() and _colors == 'on'):
        from kamaki.cli.utils import remove_colors
        remove_colors()

    cloud = arguments['cloud'].value or _cnf.value.get(
        'global', 'default_cloud')
    if not cloud:
        num_of_clouds = len(_cnf.value.keys('cloud'))
        if num_of_clouds == 1:
            cloud = _cnf.value.keys('cloud')[0]
        elif num_of_clouds > 1:
            raise CLIError(
                'Found %s clouds but none of them is set as default' % (
                    num_of_clouds),
                importance=2, details=[
                    'Please, choose one of the following cloud names:',
                    ', '.join(_cnf.value.keys('cloud')),
                    'To see all cloud settings:',
                    '  kamaki config get cloud.<cloud name>',
                    'To set a default cloud:',
                    '  kamaki config set default_cloud <cloud name>',
                    'To pick a cloud for the current session, use --cloud:',
                    '  kamaki --cloud=<cloud name> ...'])
    if not cloud in _cnf.value.keys('cloud'):
        raise CLIError(
            'No cloud%s is configured' % ((' "%s"' % cloud) if cloud else ''),
            importance=3, details=[
                'To configure a new cloud "%s", find and set the' % (
                    cloud or '<cloud name>'),
                'single authentication URL and token:',
                '  kamaki config set cloud.%s.url <URL>' % (
                    cloud or '<cloud name>'),
                '  kamaki config set cloud.%s.token <t0k3n>' % (
                    cloud or '<cloud name>')])
    auth_args = dict()
    for term in ('url', 'token'):
        try:
            auth_args[term] = _cnf.get_cloud(cloud, term)
        except KeyError or IndexError:
            auth_args[term] = ''
        if not auth_args[term]:
            raise CLIError(
                'No authentication %s provided for cloud "%s"' % (
                    term.upper(), cloud),
                importance=3, details=[
                    'Set a %s for cloud %s:' % (term.upper(), cloud),
                    '  kamaki config set cloud.%s.%s <%s>' % (
                        cloud, term, term.upper())])
    return cloud


def init_cached_authenticator(config_argument, cloud, logger):
    try:
        _cnf = config_argument.value
        url = _cnf.get_cloud(cloud, 'url')
        tokens = _cnf.get_cloud(cloud, 'token').split()
        auth_base, failed = None, []
        for token in tokens:
            try:
                if auth_base:
                    auth_base.authenticate(token)
                else:
                    tmp_base = CachedAstakosClient(url, token)
                    from kamaki.cli.commands import _command_init
                    fake_cmd = _command_init(dict(config=config_argument))
                    fake_cmd.client = auth_base
                    fake_cmd._set_log_params()
                    tmp_base.authenticate(token)
                    auth_base = tmp_base
            except ClientError as ce:
                if ce.status in (401, ):
                    logger.warning(
                        'WARNING: Failed to authenticate token %s' % token)
                    failed.append(token)
                else:
                    raise
        for token in failed:
            r = raw_input(
                'Token %s failed to authenticate. Remove it? [y/N]: ' % token)
            if r in ('y', 'Y'):
                tokens.remove(token)
        if set(failed).difference(tokens):
            _cnf.set_cloud(cloud, 'token', ' '.join(tokens))
            _cnf.write()
        if tokens:
            return auth_base
        logger.warning('WARNING: cloud.%s.token is now empty' % cloud)
    except AssertionError as ae:
        logger.warning('WARNING: Failed to load authenticator [%s]' % ae)
    return None


def _load_spec_module(spec, arguments, module):
    global kloger
    if not spec:
        return None
    pkg = None
    for location in cmd_spec_locations:
        location += spec if location == '' else '.%s' % spec
        try:
            kloger.debug('Import %s from %s' % ([module], location))
            pkg = __import__(location, fromlist=[module])
            kloger.debug('\t...OK')
            return pkg
        except ImportError as ie:
            kloger.debug('\t...Failed')
            continue
    if not pkg:
        msg = 'Loading command group %s failed: %s' % (spec, ie)
        msg += '\nHINT: use a text editor to remove all global.*_cli'
        msg += '\n\tsettings from the configuration file'
        kloger.debug(msg)
    return pkg


def _groups_help(arguments):
    global _debug
    global kloger
    descriptions = {}
    acceptable_groups = arguments['config'].groups
    for cmd_group, spec in arguments['config'].cli_specs:
        pkg = _load_spec_module(spec, arguments, '_commands')
        if pkg:
            cmds = getattr(pkg, '_commands')
            try:
                for cmd_tree in cmds:
                    if cmd_tree.name in acceptable_groups:
                        descriptions[cmd_tree.name] = cmd_tree.description
            except TypeError:
                if _debug:
                    kloger.warning(
                        'No cmd description (help) for module %s' % cmd_group)
        elif _debug:
            kloger.warning('Loading of %s cmd spec failed' % cmd_group)
    print('\nOptions:\n - - - -')
    print_dict(descriptions)


def _load_all_commands(cmd_tree, arguments):
    _cnf = arguments['config']
    for cmd_group, spec in _cnf.cli_specs:
        try:
            spec_module = _load_spec_module(spec, arguments, '_commands')
            spec_commands = getattr(spec_module, '_commands')
        except AttributeError:
            if _debug:
                global kloger
                kloger.warning('No valid description for %s' % cmd_group)
            continue
        for spec_tree in spec_commands:
            if spec_tree.name == cmd_group:
                cmd_tree.add_tree(spec_tree)
                break


#  Methods to be used by CLI implementations


def print_subcommands_help(cmd):
    printout = {}
    for subcmd in cmd.subcommands.values():
        spec, sep, print_path = subcmd.path.partition('_')
        printout[print_path.replace('_', ' ')] = subcmd.help
    if printout:
        print('\nOptions:\n - - - -')
        print_dict(printout)


def update_parser_help(parser, cmd):
    global _best_match
    parser.syntax = parser.syntax.split('<')[0]
    parser.syntax += ' '.join(_best_match)

    description = ''
    if cmd.is_command:
        cls = cmd.cmd_class
        parser.syntax += ' ' + cls.syntax
        parser.update_arguments(cls().arguments)
        description = getattr(cls, 'long_description', '').strip()
    else:
        parser.syntax += ' <...>'
    parser.parser.description = (
        cmd.help + ('\n' if description else '')) if cmd.help else description


def print_error_message(cli_err, out=stderr):
    errmsg = '%s' % cli_err
    if cli_err.importance == 1:
        errmsg = magenta(errmsg)
    elif cli_err.importance == 2:
        errmsg = yellow(errmsg)
    elif cli_err.importance > 2:
        errmsg = red(errmsg)
    out.write(errmsg)
    for errmsg in cli_err.details:
        out.write('|  %s\n' % errmsg)
        out.flush()


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
    groups = arguments['config'].groups
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

def is_non_API(parser):
    nonAPIs = ('history', 'config')
    for term in parser.unparsed:
        if not term.startswith('-'):
            if term in nonAPIs:
                return True
            return False
    return False


def main(func):
    def wrap():
        try:
            exe = basename(argv[0])
            parser = ArgumentParseManager(exe)

            if parser.arguments['version'].value:
                exit(0)

            _cnf = parser.arguments['config']
            log_file = _cnf.get('global', 'log_file')
            if log_file:
                logger.set_log_filename(log_file)
            global filelog
            filelog = logger.add_file_logger(__name__.split('.')[0])
            filelog.info('* Initial Call *\n%s\n- - -' % ' '.join(argv))

            from kamaki.cli.utils import suggest_missing
            global _colors
            exclude = ['ansicolors'] if not _colors == 'on' else []
            suggest_missing(exclude=exclude)
            func(exe, parser)
        except CLIError as err:
            print_error_message(err)
            if _debug:
                raise err
            exit(1)
        except KeyboardInterrupt:
            print('Canceled by user')
            exit(1)
        except Exception as er:
            print('Unknown Error: %s' % er)
            if _debug:
                raise
            exit(1)
    return wrap


@main
def run_shell(exe, parser):
    parser.arguments['help'].value = False
    cloud = _init_session(parser.arguments)
    from command_shell import _init_shell
    global kloger
    _cnf = parser.arguments['config']
    auth_base = init_cached_authenticator(_cnf, cloud, kloger)
    try:
        username, userid = (
            auth_base.user_term('name'), auth_base.user_term('id'))
    except Exception:
        username, userid = '', ''
    shell = _init_shell(exe, parser, username, userid)
    _load_all_commands(shell.cmd_tree, parser.arguments)
    shell.run(auth_base, cloud, parser)


@main
def run_one_cmd(exe, parser):
    cloud = _init_session(parser.arguments, is_non_API(parser))
    if parser.unparsed:
        global _history
        try:
            token = parser.arguments['config'].get_cloud(
                cloud, 'token').split()[0]
        except Exception:
            token = None
        _history = History(
            parser.arguments['config'].get('global', 'history_file'),
            token=token)
        _history.add(' '.join([exe] + argv[1:]))
        from kamaki.cli import one_command
        one_command.run(cloud, parser, _help)
    else:
        parser.print_help()
        _groups_help(parser.arguments)
        print('kamaki-shell: An interactive command line shell')
