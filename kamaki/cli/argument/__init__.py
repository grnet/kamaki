# Copyright 2012-2015 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or
# without modification, are permitted provided that the following
# conditions are met:
#
#   1. Redistributions of source code must retain the above
#     copyright notice, this list of conditions and the following
#     disclaimer.
#
#   2. Redistributions in binary form must reproduce the above
#     copyright notice, this list of conditions and the following
#     disclaimer in the documentation and/or other materials
#     provided with the distribution.
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

from kamaki.cli.config import Config
from kamaki.cli.errors import (
    CLISyntaxError, raiseCLIError, CLIInvalidArgument)
from kamaki.cli.utils import split_input, to_bytes

from datetime import datetime as dtm
import dateutil.tz
import dateutil.parser
from time import mktime
from sys import stderr
import os.path

from logging import getLogger
from argparse import (
    ArgumentParser, ArgumentError, RawDescriptionHelpFormatter)
from progress.bar import ShadyBar as KamakiProgressBar

log = getLogger(__name__)


class NoAbbrArgumentParser(ArgumentParser):
    """This is Argument Parser with disabled argument abbreviation"""

    def _get_option_tuples(self, option_string):
        result = []
        chars = self.prefix_chars
        if option_string[0] in chars and option_string[1] in chars:
            if '=' in option_string:
                option_prefix, explicit_arg = option_string.split('=', 1)
            else:
                option_prefix = option_string
                explicit_arg = None
            for option_string in self._option_string_actions:
                if option_string == option_prefix:
                    action = self._option_string_actions[option_string]
                    tup = action, option_string, explicit_arg
                    result.append(tup)
        elif option_string[0] in chars and option_string[1] not in chars:
            option_prefix = option_string
            explicit_arg = None
            short_option_prefix = option_string[:2]
            short_explicit_arg = option_string[2:]

            for option_string in self._option_string_actions:
                if option_string == short_option_prefix:
                    action = self._option_string_actions[option_string]
                    tup = action, option_string, short_explicit_arg
                    result.append(tup)
                elif option_string == option_prefix:
                    action = self._option_string_actions[option_string]
                    tup = action, option_string, explicit_arg
                    result.append(tup)
        else:
            return super(
                NoAbbrArgumentParser, self)._get_option_tuples(option_string)
        return result


class Argument(object):
    """An argument that can be parsed from command line or otherwise.
    This is the top-level Argument class. It is suggested to extent this
    class into more specific argument types.
    """
    lvalue_delimiter = '/'

    def __init__(self, arity, help=None, parsed_name=None, default=None):
        self.arity = int(arity)
        self.help = '%s' % help or ''

        assert parsed_name, 'No parsed name for argument %s' % self
        self.parsed_name = list(parsed_name) if isinstance(
            parsed_name, list) or isinstance(parsed_name, tuple) else (
                '%s' % parsed_name).split()
        for name in self.parsed_name:
            assert name.count(' ') == 0, '%s: Invalid parse name "%s"' % (
                self, name)
            msg = '%s: Invalid parse name "%s" should start with a "-"' % (
                self, name)
            assert name.startswith('-'), msg

        self.default = default or None

    @property
    def value(self):
        return getattr(self, '_value', self.default)

    @value.setter
    def value(self, newvalue):
        self._value = newvalue

    def update_parser(self, parser, name):
        """Update argument parser with self info"""
        action = 'append' if self.arity < 0 else (
            'store' if self.arity else 'store_true')
        parser.add_argument(
            *self.parsed_name,
            dest=name, action=action, default=self.default, help=self.help)

    @property
    def lvalue(self):
        """A printable form of the left value when calling an argument e.g.,
        --left-value=right-value"""
        return (self.lvalue_delimiter or ' ').join(self.parsed_name or [])


class ConfigArgument(Argument):
    """Manage a kamaki configuration (file)"""

    def __init__(self, help, parsed_name=('-c', '--config')):
        super(ConfigArgument, self).__init__(1, help, parsed_name, None)
        self.file_path = None

    @property
    def value(self):
        return getattr(self, '_value', None)

    @value.setter
    def value(self, config_file):
        if config_file:
            if not os.path.exists(config_file):
                raiseCLIError(
                    'Config file "%s" does not exist' % config_file,
                    importance=3)
            self._value = Config(config_file)
            self.file_path = config_file
        elif self.file_path:
            self._value = Config(self.file_path)
        else:
            self._value = Config()

    def get(self, group, term):
        """Get a configuration setting from the Config object"""
        return self.value.get(group, term)

    @property
    def groups(self):
        suffix = '_cli'
        slen = len(suffix)
        return [term[:-slen] for term in self.value.keys('global') if (
            term.endswith(suffix))]

    @property
    def cli_specs(self):
        suffix = '_cli'
        slen = len(suffix)
        return [(k[:-slen], v) for k, v in self.value.items('global') if (
            k.endswith(suffix))]

    def get_global(self, option):
        return self.value.get('global', option)

    def get_cloud(self, cloud, option):
        return self.value.get_cloud(cloud, option)


class RuntimeConfigArgument(Argument):
    """Set a run-time setting option (not persistent)"""

    def __init__(self, config_arg, help='', parsed_name=None, default=None):
        super(self.__class__, self).__init__(1, help, parsed_name, default)
        self._config_arg = config_arg

    @property
    def value(self):
        return super(RuntimeConfigArgument, self).value

    @value.setter
    def value(self, options):
        if options == self.default:
            return
        if not isinstance(options, list):
            options = ['%s' % options]
        for option in options:
            keypath, sep, val = option.partition('=')
            if not sep:
                raiseCLIError(
                    CLISyntaxError('Argument Syntax Error '),
                    details=[
                        '%s is missing a "="',
                        ' (usage: -o section.key=val)' % option])
            section, sep, key = keypath.partition('.')
        if not sep:
            key = section
            section = 'global'
        self._config_arg.value.override(
            section.strip(),
            key.strip(),
            val.strip())


class FlagArgument(Argument):
    """
    :value: true if set, false otherwise
    """

    def __init__(self, help='', parsed_name=None, default=None):
        super(FlagArgument, self).__init__(0, help, parsed_name, default)


class ValueArgument(Argument):
    """
    :value type: string
    :value returns: given value or default
    """

    def __init__(self, help='', parsed_name=None, default=None):
        super(ValueArgument, self).__init__(1, help, parsed_name, default)


class BooleanArgument(ValueArgument):
    """Can be true, false or None (Flag argument can only be true or None)"""

    @property
    def value(self):
        return getattr(self, '_value', None)

    @value.setter
    def value(self, new_value):
        if new_value:
            v = new_value.lower()
            if v not in ('true', 'false'):
                raise CLIInvalidArgument(
                    'Invalid value %s=%s' % (self.lvalue, new_value),
                    details=['Usage:', '%s=<true|false>' % self.lvalue])
            self._value = bool(v == 'true')


class CommaSeparatedListArgument(ValueArgument):
    """
    :value type: string
    :value returns: list of the comma separated values
    """

    @property
    def value(self):
        return self._value or list()

    @value.setter
    def value(self, newvalue):
        self._value = newvalue.split(',') if newvalue else list()


class IntArgument(ValueArgument):

    @property
    def value(self):
        """integer (type checking)"""
        return getattr(self, '_value', self.default)

    @value.setter
    def value(self, newvalue):
        if newvalue == self.default:
            self._value = newvalue
            return
        try:
            if int(newvalue) == float(newvalue):
                self._value = int(newvalue)
            else:
                raise ValueError('Raise int argument error')
        except ValueError:
            raiseCLIError(CLISyntaxError(
                'IntArgument Error',
                details=['Value %s not an int' % newvalue]))


class DataSizeArgument(ValueArgument):
    """Input: a string of the form <number><unit>
    Output: the number of bytes
    Units: B, KiB, KB, MiB, MB, GiB, GB, TiB, TB
    """

    @property
    def value(self):
        return getattr(self, '_value', self.default)

    def _calculate_limit(self, user_input):
        limit = 0
        try:
            limit = int(user_input)
        except ValueError:
            index = 0
            digits = ['%s' % num for num in range(0, 10)] + ['.']
            while user_input[index] in digits:
                index += 1
            limit = user_input[:index]
            format = user_input[index:]
            try:
                return to_bytes(limit, format)
            except Exception as qe:
                msg = 'Failed to convert %s to bytes' % user_input,
                raiseCLIError(qe, msg, details=[
                    'Syntax: containerlimit set <limit>[format] [container]',
                    'e.g.,: containerlimit set 2.3GB mycontainer',
                    'Valid formats:',
                    '(*1024): B, KiB, MiB, GiB, TiB',
                    '(*1000): B, KB, MB, GB, TB'])
        return limit

    @value.setter
    def value(self, new_value):
        if new_value:
            self._value = self._calculate_limit(new_value)


class UserAccountArgument(ValueArgument):
    """A user UUID or name (if uuid does not exist)"""

    account_client = None

    @property
    def value(self):
        return super(UserAccountArgument, self).value

    @value.setter
    def value(self, uuid_or_name):
        if uuid_or_name and self.account_client:
            r = self.account_client.uuids2usernames([uuid_or_name, ])
            if r:
                self._value = uuid_or_name
            else:
                r = self.account_client.usernames2uuids([uuid_or_name])
                self._value = r.get(uuid_or_name) if r else None
            if not self._value:
                raise raiseCLIError('User name or UUID not found', details=[
                    '%s is not a known username or UUID' % uuid_or_name,
                    'Usage:  %s <USER_UUID | USERNAME>' % self.lvalue])


class DateArgument(ValueArgument):

    DATE_FORMATS = ['%a %b %d %H:%M:%S %Y', '%d-%m-%Y', '%H:%M:%S %d-%m-%Y']
    INPUT_FORMATS = [
        'YYYY-mm-dd', '"HH:MM:SS YYYY-mm-dd"', 'YYYY-mm-ddTHH:MM:SS+TMZ',
        '"Day Mon dd HH:MM:SS YYYY"']

    @property
    def timestamp(self):
        v = getattr(self, '_value', self.default)
        return mktime(v.timetuple()) if v else None

    @property
    def formated(self):
        v = getattr(self, '_value', self.default)
        return v.strftime(self.DATE_FORMATS[0]) if v else None

    @property
    def value(self):
        return self.timestamp

    @property
    def isoformat(self):
        d = getattr(self, '_value', self.default)
        if not d:
            return None
        if not d.tzinfo:
            d = d.replace(tzinfo=dateutil.tz.tzlocal())
        return d.isoformat()

    @value.setter
    def value(self, newvalue):
        if newvalue:
            try:
                self._value = dateutil.parser.parse(newvalue)
            except Exception:
                raise CLIInvalidArgument(
                    'Invalid value "%s" for date argument %s' % (
                        newvalue, self.lvalue),
                    details=['Suggested formats:'] + self.INPUT_FORMATS)

    def format_date(self, datestr):
        for fmt in self.DATE_FORMATS:
            try:
                return dtm.strptime(datestr, fmt)
            except ValueError as ve:
                continue
        raise raiseCLIError(ve, 'Failed to format date', details=[
            '%s could not be formated for HTTP headers' % datestr])


class VersionArgument(FlagArgument):
    """A flag argument with that prints current version"""

    @property
    def value(self):
        """bool"""
        return super(self.__class__, self).value

    @value.setter
    def value(self, newvalue):
        self._value = newvalue
        if newvalue:
            import kamaki
            print('kamaki %s' % kamaki.__version__)


class RepeatableArgument(Argument):
    """A value argument that can be repeated"""

    def __init__(self, help='', parsed_name=None, default=None):
        super(RepeatableArgument, self).__init__(
            -1, help, parsed_name, default)

    @property
    def value(self):
        return getattr(self, '_value', [])

    @value.setter
    def value(self, newvalue):
        self._value = newvalue


class KeyValueArgument(Argument):
    """A Key=Value Argument that can be repeated

    :syntax: --<arg> key1=value1 --<arg> key2=value2 ...
    """

    def __init__(self, help='', parsed_name=None, default=None):
        super(KeyValueArgument, self).__init__(-1, help, parsed_name, default)

    @property
    def value(self):
        """
        :returns: (dict) {key1: val1, key2: val2, ...}
        """
        return getattr(self, '_value', {})

    @value.setter
    def value(self, keyvalue_pairs):
        """
        :param keyvalue_pairs: (str) ['key1=val1', 'key2=val2', ...]
        """
        if keyvalue_pairs:
            self._value = self.value
            try:
                for pair in keyvalue_pairs:
                    key, sep, val = pair.partition('=')
                    assert sep, ' %s misses a "=" (usage: key1=val1 )\n' % (
                        pair)
                    self._value[key] = val
            except Exception as e:
                raiseCLIError(e, 'KeyValueArgument Syntax Error')


class StatusArgument(ValueArgument):
    """Initialize with valid_states=['list', 'of', 'states']
    First state is the default"""

    def __init__(self, *args, **kwargs):
        self.valid_states = [
            s.upper() for s in kwargs.pop('valid_states', ['BUILD', ])]
        super(StatusArgument, self).__init__(*args, **kwargs)

    @property
    def value(self):
        return getattr(self, '_value', None)

    @value.setter
    def value(self, new_status):
        if new_status:
            new_status = new_status.upper()
            if new_status not in self.valid_states:
                raise CLIInvalidArgument(
                    'Invalid argument %s' % new_status,
                    details=['Usage:', '%s=[%s]' % (
                        self.lvalue, '|'.join(self.valid_states))])
            self._value = new_status


class ProgressBarArgument(FlagArgument):
    """Manage a progress bar"""

    def __init__(self, help='', parsed_name='', default=True):
        self.suffix = '%(percent)d%%'
        super(ProgressBarArgument, self).__init__(help, parsed_name, default)

    def clone(self):
        """Get a modifiable copy of this bar"""
        newarg = ProgressBarArgument(
            self.help, self.parsed_name, self.default)
        newarg._value = self._value
        return newarg

    def get_generator(
            self, message, message_len=25, countdown=False, timeout=100):
        """Get a generator to handle progress of the bar (gen.next())"""
        if self.value:
            return None
        try:
            self.bar = KamakiProgressBar(
                message.ljust(message_len), max=timeout or 100)
        except NameError:
            self.value = None
            return self.value
        if countdown:
            bar_phases = list(self.bar.phases)
            self.bar.empty_fill, bar_phases[0] = bar_phases[-1], ''
            bar_phases.reverse()
            self.bar.phases = bar_phases
            self.bar.bar_prefix = ' '
            self.bar.bar_suffix = ' '
            self.bar.suffix = '%(remaining)ds to timeout'
        else:
            self.bar.suffix = '%(percent)d%% - %(eta)ds'
        self.bar.start()

        def progress_gen(n):
            for i in self.bar.iter(range(int(n))):
                yield
            yield
        return progress_gen

    def finish(self):
        """Stop progress bar, return terminal cursor to user"""
        if self.value:
            return
        mybar = getattr(self, 'bar', None)
        if mybar:
            mybar.finish()


class PithosLocationArgument(ValueArgument):
    """Resolve pithos URI, return in the form pithos://uuid/container[/object]

    UPDATE: URLs without an object are also resolvable. Therefore, caller
    methods should check if there is an object or not
    """

    def __init__(
            self, help=None, parsed_name=None, default=None, user_uuid=None):
        super(PithosLocationArgument, self).__init__(
            help=help, parsed_name=parsed_name, default=default)
        self.uuid, self.container, self.object = user_uuid, None, None

    def setdefault(self, term, value):
        if not getattr(self, term, None):
            setattr(self, term, value)

    @property
    def dict(self):
        """:returns: location as {user_uuid: .., container: .., object: ..}"""
        return dict(
            user_uuid=self.uuid, container=self.container, object=self.object)

    @property
    def tuple(self):
        """returns: location as (user_uuid, container, object)"""
        return (self.uuid, self.container, self.object)

    @property
    def value(self):
        object_ = ('/%s' % self.object) if self.object else ''
        return 'pithos://%s/%s%s' % (self.uuid, self.container, object_)

    @value.setter
    def value(self, location):
        if location:
            from kamaki.cli.cmds.pithos import _PithosContainer as pc
            try:
                uuid, self.container, self.object = pc.resolve_pithos_url(
                    location)
                self.uuid = uuid or self.uuid
                assert self.container, 'No container in pithos URI'
            except Exception as e:
                raise CLIInvalidArgument(
                    'Invalid Pithos+ location %s (%s)' % (location, e),
                    details=[
                        'The image location must be a valid Pithos+',
                        'location. There are two valid formats:',
                        '  pithos://USER_UUID/CONTAINER[/OBJECT]',
                        'OR',
                        '  /CONTAINER/OBJECT]',
                        'To see all containers:',
                        '  [kamaki] container list',
                        'To list the contents of a container:',
                        '  [kamaki] container list CONTAINER'])


#  Initial command line interface arguments


class ArgumentParseManager(object):
    """Manage (initialize and update) an ArgumentParser object"""

    def __init__(
            self, exe, arguments,
            required=None, syntax=None, description=None, check_required=True):
        """
        :param exe: (str) the basic command (e.g. 'kamaki')

        :param arguments: (dict) if given, overrides the global _argument as
            the parsers arguments specification
        :param required: (list or tuple) an iterable of argument keys, denoting
            which arguments are required. A tuple denoted an AND relation,
            while a list denotes an OR relation e.g., ['a', 'b'] means that
            either 'a' or 'b' is required, while ('a', 'b') means that both 'a'
            and 'b' ar required.
            Nesting is allowed e.g., ['a', ('b', 'c'), ['d', 'e']] means that
            this command required either 'a', or both 'b' and 'c', or one of
            'd', 'e'.
            Repeated arguments are also allowed e.g., [('a', 'b'), ('a', 'c'),
            ['b', 'c']] means that the command required either 'a' and 'b' or
            'a' and 'c' or at least one of 'b', 'c' and could be written as
            [('a', ['b', 'c']), ['b', 'c']]
        :param syntax: (str) The basic syntax of the arguments. Default:
            exe <cmd_group> [<cmd_subbroup> ...] <cmd>
        :param description: (str) The description of the commands or ''
        :param check_required: (bool) Set to False inorder not to check for
            required argument values while parsing
        """
        self.parser = NoAbbrArgumentParser(
            add_help=False, formatter_class=RawDescriptionHelpFormatter)
        self._exe = exe
        self.syntax = syntax or (
            '%s <cmd_group> [<cmd_subbroup> ...] <cmd>' % exe)
        self.required, self.check_required = required, check_required
        self.parser.description = description or ''
        self.arguments = arguments
        self._parser_modified, self._parsed, self._unparsed = False, None, None
        self.parse()

    @staticmethod
    def required2list(required):
        if isinstance(required, list) or isinstance(required, tuple):
            terms = []
            for r in required:
                terms.append(ArgumentParseManager.required2list(r))
            return list(set(terms).union())
        return required

    @staticmethod
    def required2str(required, arguments, tab=''):
        if isinstance(required, list):
            return ' %sat least one of the following:\n%s' % (tab, ''.join(
                [ArgumentParseManager.required2str(
                    r, arguments, tab + '  ') for r in required]))
        elif isinstance(required, tuple):
            return ' %sall of the following:\n%s' % (tab, ''.join(
                [ArgumentParseManager.required2str(
                    r, arguments, tab + '  ') for r in required]))
        else:
            lt_pn, lt_all, arg = 23, 80, arguments[required]
            tab2 = ' ' * lt_pn
            ret = '%s%s' % (tab, ', '.join(arg.parsed_name))
            if arg.arity != 0:
                ret += ' %s' % required.upper()
            ret = ('{:<%s}' % lt_pn).format(ret)
            prefix = ('\n%s' % tab2) if len(ret) > lt_pn else ' '
            cur = 0
            while arg.help[cur:]:
                next = cur + lt_all - lt_pn
                ret += prefix
                ret += ('{:<%s}' % (lt_all - lt_pn)).format(arg.help[cur:next])
                cur = next
            return ret + '\n'

    @staticmethod
    def _patch_with_required_args(arguments, required):
        if isinstance(required, tuple):
            return ' '.join([ArgumentParseManager._patch_with_required_args(
                arguments, k) for k in required])
        elif isinstance(required, list):
            return '< %s >' % ' | '.join([
                ArgumentParseManager._patch_with_required_args(
                    arguments, k) for k in required])
        arg = arguments[required]
        return '/'.join(arg.parsed_name) + (
            ' %s [...]' % required.upper() if arg.arity < 0 else (
                ' %s' % required.upper() if arg.arity else ''))

    def print_help(self, out=stderr):
        if self.required:
            tmp_args = dict(self.arguments)
            for term in self.required2list(self.required):
                tmp_args.pop(term)
            tmp_parser = ArgumentParseManager(self._exe, tmp_args)
            tmp_parser.syntax = self.syntax + self._patch_with_required_args(
                self.arguments, self.required)
            tmp_parser.parser.description = '%s\n\nrequired arguments:\n%s' % (
                self.parser.description,
                self.required2str(self.required, self.arguments))
            tmp_parser.update_parser()
            tmp_parser.parser.print_help()
        else:
            self.parser.print_help()

    @property
    def syntax(self):
        """The command syntax (useful for help messages, descriptions, etc)"""
        return self.parser.prog

    @syntax.setter
    def syntax(self, new_syntax):
        self.parser.prog = new_syntax

    @property
    def arguments(self):
        """:returns: (dict) arguments the parser should be aware of"""
        return self._arguments

    @arguments.setter
    def arguments(self, new_arguments):
        assert isinstance(new_arguments, dict), 'Arguments must be in a dict'
        self._arguments = new_arguments
        self.update_parser()

    @property
    def parsed(self):
        """(Namespace) parser-matched terms"""
        if self._parser_modified:
            self.parse()
        return self._parsed

    @property
    def unparsed(self):
        """(list) parser-unmatched terms"""
        if self._parser_modified:
            self.parse()
        return self._unparsed

    def update_parser(self, arguments=None):
        """Load argument specifications to parser

        :param arguments: if not given, update self.arguments instead
        """
        arguments = arguments or self._arguments

        for name, arg in arguments.items():
            try:
                arg.update_parser(self.parser, name)
                self._parser_modified = True
            except ArgumentError:
                pass

    def update_arguments(self, new_arguments):
        """Add to / update existing arguments

        :param new_arguments: (dict)
        """
        if new_arguments:
            assert isinstance(new_arguments, dict), 'Arguments not in dict !!!'
            self._arguments.update(new_arguments)
            self.update_parser()

    def _parse_required_arguments(self, required, parsed_args):
        if not (self.check_required and required):
            return True
        if isinstance(required, tuple):
            for item in required:
                if not self._parse_required_arguments(item, parsed_args):
                    return False
            return True
        elif isinstance(required, list):
            for item in required:
                if self._parse_required_arguments(item, parsed_args):
                    return True
            return False
        return required in parsed_args

    def parse(self, new_args=None):
        """Parse user input"""
        try:
            pkargs = (new_args,) if new_args else ()
            self._parsed, unparsed = self.parser.parse_known_args(*pkargs)
            parsed_args = [
                k for k, v in vars(self._parsed).items() if v not in (None, )]
            if not self._parse_required_arguments(self.required, parsed_args):
                self.print_help()
                raise CLISyntaxError('Missing required arguments')
        except SystemExit:
            raiseCLIError(CLISyntaxError('Argument Syntax Error'))
        for name, arg in self.arguments.items():
            arg.value = getattr(self._parsed, name, arg.default)
        self._unparsed = []
        for term in unparsed:
            self._unparsed += split_input(' \'%s\' ' % term)
        self._parser_modified = False
