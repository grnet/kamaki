# Copyright 2012-2015 GRNET S.A. All rights reserved.
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
import os
from os.path import basename, exists
from inspect import getargspec

from kamaki.cli.argument import (
    ArgumentParseManager, ConfigArgument, ValueArgument, FlagArgument,
    RuntimeConfigArgument, VersionArgument, Argument)
from kamaki.cli.history import History
from kamaki.cli.utils import (
    print_dict, magenta, red, yellow, suggest_missing, remove_colors, pref_enc)
from kamaki.cli.errors import CLIError, CLICmdSpecError
from kamaki.cli import logger
from kamaki.clients.astakos import CachedAstakosClient
from kamaki.clients import ClientError, KamakiSSLError, DEBUGV
from kamaki.clients.utils import https, escape_ctrl_chars


_debug = False
kloger = None
DEF_CLOUD_ENV = 'KAMAKI_DEFAULT_CLOUD'

#  command auxiliary methods

_best_match = []


def _arg2syntax(arg):
    return arg.replace(
        '____', '[:').replace(
            '___', ':').replace(
                '__', ']').replace(
                    '_', ' ')


def _update_best_match(name_terms, prefix=[]):
    global _best_match
    if prefix:
        pref_list = prefix if isinstance(prefix, list) else prefix.split('_')
    else:
        _best_match, pref_list = [], []

    if pref_list:
        num_of_matching_terms = 0
        for i, term in enumerate(name_terms):
            try:
                if term == pref_list[i]:
                    num_of_matching_terms += 1
                else:
                    break
            except IndexError:
                break
    else:
        num_of_matching_terms = len(name_terms)

    if num_of_matching_terms and len(_best_match) <= num_of_matching_terms:
        if len(_best_match) < num_of_matching_terms:
            _best_match = name_terms[:num_of_matching_terms]
        return True
    return False


def command(cmd_tree, prefix='', descedants_depth=1):
    """Load a class as a command
        e.g., spec_cmd0_cmd1 will be command spec cmd0

        :param cmd_tree: is initialized in cmd_spec file and is the structure
            where commands are loaded. Var name should be "namespaces"
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
        #  Build command syntax help
        spec = getargspec(cls.main.im_func)
        args = spec.args[1:]
        n = len(args) - len(spec.defaults or ())
        required = ' '.join(['<%s>' % _arg2syntax(x) for x in args[:n]])
        optional = ' '.join(['[%s]' % _arg2syntax(x) for x in args[n:]])
        cls.syntax = ' '.join([required, optional])
        if spec.varargs:
            cls.syntax += ' <%s ...>' % spec.varargs

        cmd_tree.add_command(
            cls_name, cls.description, cls, cls.long_description)
        return cls
    return wrap


cmd_spec_locations = [
    'kamaki.cli.cmds',
    'kamaki.cmds',
    'kamaki.cli.commands',
    'kamaki.commands',
    'kamaki.cli',
    'kamaki',
    '']


#  Generic init auxiliary functions


def _setup_logging(debug=False, verbose=False, _verbose_with_data=False):
    """handle logging for clients package"""

    sfmt, rfmt = '> %(message)s', '< %(message)s'
    if debug:
        print('Logging location: %s' % logger.get_log_filename())
        logger.add_stream_logger('kamaki.clients.send', logging.DEBUG, sfmt)
        logger.add_stream_logger('kamaki.clients.recv', logging.DEBUG, rfmt)
        logger.add_stream_logger(__name__, logging.DEBUG)
    elif verbose:
        logger.add_stream_logger('kamaki.clients.send', DEBUGV, sfmt)
        logger.add_stream_logger('kamaki.clients.recv', DEBUGV, rfmt)
        logger.add_stream_logger(__name__, DEBUGV)
    # else:
    #     logger.add_stream_logger(__name__, logging.WARNING)
    if _verbose_with_data:
        from kamaki import clients
        clients.Client.LOG_DATA = True
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
        stdout.write('Create (overwrite) file %s ? [y/N] ' % escape_ctrl_chars(
            cnf.path))
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


def _init_session(arguments, is_non_api=False):
    """
    :returns: cloud name
    """
    _help = arguments['help'].value
    global _debug
    _debug = arguments['debug'].value
    _verbose_with_data = arguments['verbose_with_data'].value
    _verbose = arguments['verbose'].value or _verbose_with_data
    _cnf = arguments['config']

    _setup_logging(_debug, _verbose, _verbose_with_data)

    if _help or is_non_api:
        return None

    #  Patch https for SSL Authentication
    ca_file = arguments['ca_file'].value or _cnf.get('global', 'ca_certs')
    ignore_ssl = arguments['ignore_ssl'].value or (
        _cnf.get('global', 'ignore_ssl').lower() == 'on')

    if ca_file:
        try:
            https.patch_with_certs(ca_file)
        except https.SSLUnicodeError as sslu:
            raise CLIError(
                'Failed to set CA certificates file %s' % ca_file,
                importance=2, details=[
                    'SSL module cannot handle non-ascii file names',
                    'Check the file path and consider moving and renaming',
                    'To set the new CA certificates path',
                    '    kamaki config set ca_certs CA_FILE',
                    sslu, ])
    else:
        warn = red('CA certifications path not set (insecure) ')
        kloger.warning(warn)
    https.patch_ignore_ssl(ignore_ssl)

    _check_config_version(_cnf.value)

    _colors = _cnf.value.get('global', 'colors')
    if not (stdout.isatty() and _colors == 'on'):
        remove_colors()

    cloud = arguments['cloud'].value or _cnf.value.get(
        'global', 'default_cloud') or os.environ.get(DEF_CLOUD_ENV)
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
                    '  or set the %s enviroment variable' % DEF_CLOUD_ENV,
                    'To pick a cloud for the current session, use --cloud:',
                    '  kamaki --cloud=<cloud name> ...'])
    if cloud not in _cnf.value.keys('cloud'):
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
        astakos, failed, help_message = None, [], []
        for token in tokens:
            try:
                if astakos:
                    astakos.authenticate(token)
                else:
                    tmp_base = CachedAstakosClient(url, token)
                    from kamaki.cli.cmds import CommandInit
                    fake_cmd = CommandInit(dict(config=config_argument))
                    fake_cmd.client = astakos
                    fake_cmd._set_log_params()
                    tmp_base.authenticate(token)
                    astakos = tmp_base
            except ClientError as ce:
                if ce.status in (401, ):
                    logger.warning(
                        'Cloud %s failed to authenticate token %s' % (
                            cloud, token))
                    failed.append(token)
                else:
                    raise
        if failed:
            if set(tokens) == set(failed):
                tlen = len(tokens)
                logger.warning(
                    '%s token%s in cloud.%s.token failed to authenticate' % (
                        ('All %s' % tlen) if tlen > 1 else 'The only',
                        's' if tlen > 1 else '', cloud))
                help_message += [
                    'To replace with a new and valid token:',
                    '  kamaki config set cloud.%s.token NEW_TOKEN' % (cloud)]
            else:
                tlen = len(tokens)
                for token in failed:
                    tokens.remove(token)
                logger.warning(
                    '%s of %s tokens removed from cloud.%s.token list' % (
                        len(failed), tlen, cloud))
                _cnf.set_cloud(cloud, 'token', ' '.join(tokens))
                _cnf.write()
        if tokens:
            return astakos, help_message
        logger.warning('cloud.%s.token is now empty' % cloud)
        help_message = [
            'To set a new token:',
            '  kamaki config set cloud.%s.token NEW_TOKEN']
    except AssertionError as ae:
        logger.warning('Failed to load authenticator [%s]' % ae)
    return None, help_message


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
        pkg = _load_spec_module(spec, arguments, 'namespaces')
        if pkg:
            namespaces = getattr(pkg, 'namespaces')
            try:
                for cmd_tree in namespaces:
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
            spec_module = _load_spec_module(spec, arguments, 'namespaces')
            namespaces = getattr(spec_module, 'namespaces')
        except AttributeError:
            if _debug:
                global kloger
                kloger.warning('No valid description for %s' % cmd_group)
            continue
        for spec_tree in namespaces:
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
    errmsg = escape_ctrl_chars(('%s' % cli_err).strip('\n')).encode(
        pref_enc, 'replace')
    if cli_err.importance == 1:
        errmsg = magenta(errmsg)
    elif cli_err.importance == 2:
        errmsg = yellow(errmsg)
    elif cli_err.importance > 2:
        errmsg = red(errmsg)
    out.write(errmsg)
    out.write('\n')
    for errmsg in cli_err.details:
        out.write('|  %s\n' % escape_ctrl_chars(u'%s' % errmsg).encode(
            pref_enc, 'replace'))
        out.flush()


def exec_cmd(instance, cmd_args, help_method):
    try:
        return instance.main(*cmd_args)
    except TypeError as err:
        if err.args and err.args[0].startswith('main()'):
            print(magenta('Syntax error'))
            if _debug:
                raise err
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

def is_non_api(parser):
    non_apis = ('history', 'config')
    for term in parser.unparsed:
        if not term.startswith('-'):
            if term in non_apis:
                return True
            return False
    return False


def main(func):
    def wrap():
        try:
            exe = basename(argv[0])
            internal_argv = []
            for i, a in enumerate(argv):
                try:
                    internal_argv.append(a.decode(pref_enc))
                except UnicodeDecodeError as ude:
                    raise CLIError(
                        'Invalid encoding in command', importance=3, details=[
                            'The invalid term is #%s (with "%s" being 0)' % (
                                i, exe),
                            'Encoding is invalid with current locale settings '
                            '(%s)' % pref_enc,
                            '( %s )' % ude])
            for i, a in enumerate(internal_argv):
                argv[i] = a

            logger.add_stream_logger(
                __name__, logging.WARNING,
                fmt='%(levelname)s (%(name)s): %(message)s')
            _config_arg = ConfigArgument('Path to a custom config file')
            parser = ArgumentParseManager(exe, arguments=dict(
                config=_config_arg,
                cloud=ValueArgument(
                    'Chose a cloud to connect to', ('--cloud')),
                help=Argument(0, 'Show help message', ('-h', '--help')),
                debug=FlagArgument('Include debug output', ('-d', '--debug')),
                verbose=FlagArgument(
                    'Show HTTP requests and responses, without HTTP body',
                    ('-v', '--verbose')),
                verbose_with_data=FlagArgument(
                    'Show HTTP requests and responses, including HTTP body',
                    ('-vv', '--verbose-with-data')),
                version=VersionArgument(
                    'Print current version', ('-V', '--version')),
                options=RuntimeConfigArgument(
                    _config_arg,
                    'Override a config option (not persistent)',
                    ('-o', '--options')),
                ignore_ssl=FlagArgument(
                    'Allow connections to SSL sites without certs',
                    ('-k', '--ignore-ssl', '--insecure')),
                ca_file=ValueArgument(
                    'CA certificates for SSL authentication', '--ca-certs'),)
            )
            if parser.arguments['version'].value:
                exit(0)

            _cnf = parser.arguments['config']
            log_file = _cnf.get('global', 'log_file')
            if log_file:
                logger.set_log_filename(log_file)
            filelog = logger.add_file_logger(__name__.split('.')[0])

            filelog.info('%s\n- - -' % ' '.join(argv))

            _colors = _cnf.value.get('global', 'colors')
            exclude = ['ansicolors'] if not _colors == 'on' else []
            suggest_missing(exclude=exclude)
            func(exe, parser)
        except CLIError as err:
            print_error_message(err)
            if _debug:
                raise err
            exit(1)
        except KamakiSSLError as err:
            ca_arg = parser.arguments.get('ca_file')
            ca = ca_arg.value if ca_arg and ca_arg.value else _cnf.get(
                'global', 'ca_certs')
            stderr.write(red('SSL Authentication failed\n'))
            if ca:
                stderr.write('Path used for CA certifications file: %s\n' % (
                    escape_ctrl_chars(ca)))
                stderr.write('Please make sure the path is correct\n')
                if not (ca_arg and ca_arg.value):
                    stderr.write('|  To set the correct path:\n')
                    stderr.write('|    kamaki config set ca_certs CA_FILE\n')
            else:
                stderr.write('|  To use a CA certifications file:\n')
                stderr.write('|    kamaki config set ca_certs CA_FILE\n')
                stderr.write('|    OR run with --ca-certs=FILE_LOCATION\n')
            stderr.write('|  To ignore SSL errors and move on (%s):\n' % (
                red('insecure')))
            stderr.write('|    kamaki config set ignore_ssl on\n')
            stderr.write('|    OR run with --ignore-ssl\n')
            stderr.flush()
            if _debug:
                raise
            stderr.write('|  %s: %s\n' % (
                type(err), escape_ctrl_chars('%s' % err)))
            stderr.flush()
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
    global kloger
    _cnf = parser.arguments['config']
    astakos, help_message = init_cached_authenticator(_cnf, cloud, kloger)
    try:
        username, userid = (astakos.user_term('name'), astakos.user_term('id'))
    except Exception:
        username, userid = '', ''
    from kamaki.cli.shell import init_shell
    shell = init_shell(exe, parser, username, userid)
    _load_all_commands(shell.cmd_tree, parser.arguments)
    shell.run(astakos, cloud, parser)


@main
def run_one_cmd(exe, parser):
    cloud = _init_session(parser.arguments, is_non_api(parser))
    if parser.unparsed:
        global _history
        cnf = parser.arguments['config']
        try:
            token = cnf.get_cloud(cloud, 'token').split()[0]
        except Exception:
            token = None
        _history = History(cnf.get('global', 'history_file'), token=token)
        _history.limit = cnf.get('global', 'history_limit')
        _history.add(' '.join([exe] + argv[1:]))
        from kamaki.cli import one_cmd
        one_cmd.run(cloud, parser)
    else:
        parser.print_help()
        _groups_help(parser.arguments)
        print('kamaki-shell: An interactive command line shell')
