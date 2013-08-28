# Copyright 2012-2013 GRNET S.A. All rights reserved.
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
from kamaki.cli.errors import CLISyntaxError, raiseCLIError
from kamaki.cli.utils import split_input

from datetime import datetime as dtm
from time import mktime

from logging import getLogger
from argparse import ArgumentParser, ArgumentError
from argparse import RawDescriptionHelpFormatter
from progress.bar import ShadyBar as KamakiProgressBar

log = getLogger(__name__)


class Argument(object):
    """An argument that can be parsed from command line or otherwise.
    This is the top-level Argument class. It is suggested to extent this
    class into more specific argument types.
    """

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

        self.default = default if (default or self.arity) else False

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


class ConfigArgument(Argument):
    """Manage a kamaki configuration (file)"""

    def __init__(self, help, parsed_name=('-c', '--config')):
        super(ConfigArgument, self).__init__(1, help, parsed_name, None)
        self.file_path = None

    @property
    def value(self):
        return super(ConfigArgument, self).value

    @value.setter
    def value(self, config_file):
        if config_file:
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
        return self.value.get_global(option)

    def get_cloud(self, cloud, option):
        return self.value.get_cloud(cloud, option)


_config_arg = ConfigArgument('Path to config file')


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

    def __init__(self, help='', parsed_name=None, default=False):
        super(FlagArgument, self).__init__(0, help, parsed_name, default)


class ValueArgument(Argument):
    """
    :value type: string
    :value returns: given value or default
    """

    def __init__(self, help='', parsed_name=None, default=None):
        super(ValueArgument, self).__init__(1, help, parsed_name, default)


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


class DateArgument(ValueArgument):

    DATE_FORMAT = '%a %b %d %H:%M:%S %Y'

    INPUT_FORMATS = [DATE_FORMAT, '%d-%m-%Y', '%H:%M:%S %d-%m-%Y']

    @property
    def timestamp(self):
        v = getattr(self, '_value', self.default)
        return mktime(v.timetuple()) if v else None

    @property
    def formated(self):
        v = getattr(self, '_value', self.default)
        return v.strftime(self.DATE_FORMAT) if v else None

    @property
    def value(self):
        return self.timestamp

    @value.setter
    def value(self, newvalue):
        self._value = self.format_date(newvalue) if newvalue else self.default

    def format_date(self, datestr):
        for format in self.INPUT_FORMATS:
            try:
                t = dtm.strptime(datestr, format)
            except ValueError:
                continue
            return t  # .strftime(self.DATE_FORMAT)
        raiseCLIError(None, 'Date Argument Error', details=[
            '%s not a valid date' % datestr,
            'Correct formats:\n\t%s' % self.INPUT_FORMATS])


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

    def __init__(self, help='', parsed_name=None, default=[]):
        super(RepeatableArgument, self).__init__(
            -1, help, parsed_name, default)


class KeyValueArgument(Argument):
    """A Key=Value Argument that can be repeated

    :syntax: --<arg> key1=value1 --<arg> key2=value2 ...
    """

    def __init__(self, help='', parsed_name=None, default=[]):
        super(KeyValueArgument, self).__init__(-1, help, parsed_name, default)

    @property
    def value(self):
        """
        :returns: (dict) {key1: val1, key2: val2, ...}
        """
        return super(KeyValueArgument, self).value

    @value.setter
    def value(self, keyvalue_pairs):
        """
        :param keyvalue_pairs: (str) ['key1=val1', 'key2=val2', ...]
        """
        self._value = getattr(self, '_value', self.value) or {}
        try:
            for pair in keyvalue_pairs:
                key, sep, val = pair.partition('=')
                assert sep, ' %s misses a "=" (usage: key1=val1 )\n' % (pair)
                self._value[key] = val
        except Exception as e:
            raiseCLIError(e, 'KeyValueArgument Syntax Error')


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

    def get_generator(self, message, message_len=25):
        """Get a generator to handle progress of the bar (gen.next())"""
        if self.value:
            return None
        try:
            self.bar = KamakiProgressBar()
        except NameError:
            self.value = None
            return self.value
        self.bar.message = message.ljust(message_len)
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


_arguments = dict(
    config=_config_arg,
    cloud=ValueArgument('Chose a cloud to connect to', ('--cloud')),
    help=Argument(0, 'Show help message', ('-h', '--help')),
    debug=FlagArgument('Include debug output', ('-d', '--debug')),
    include=FlagArgument(
        'Include raw connection data in the output', ('-i', '--include')),
    silent=FlagArgument('Do not output anything', ('-s', '--silent')),
    verbose=FlagArgument('More info at response', ('-v', '--verbose')),
    version=VersionArgument('Print current version', ('-V', '--version')),
    options=RuntimeConfigArgument(
        _config_arg, 'Override a config value', ('-o', '--options'))
)


#  Initial command line interface arguments


class ArgumentParseManager(object):
    """Manage (initialize and update) an ArgumentParser object"""

    def __init__(self, exe, arguments=None):
        """
        :param exe: (str) the basic command (e.g. 'kamaki')

        :param arguments: (dict) if given, overrides the global _argument as
            the parsers arguments specification
        """
        self.parser = ArgumentParser(
            add_help=False, formatter_class=RawDescriptionHelpFormatter)
        self.syntax = '%s <cmd_group> [<cmd_subbroup> ...] <cmd>' % exe
        if arguments:
            self.arguments = arguments
        else:
            global _arguments
            self.arguments = _arguments
        self._parser_modified, self._parsed, self._unparsed = False, None, None
        self.parse()

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
            assert isinstance(new_arguments, dict)
            self._arguments.update(new_arguments)
            self.update_parser()

    def parse(self, new_args=None):
        """Parse user input"""
        try:
            pkargs = (new_args,) if new_args else ()
            self._parsed, unparsed = self.parser.parse_known_args(*pkargs)
        except SystemExit:
            raiseCLIError(CLISyntaxError('Argument Syntax Error'))
        for name, arg in self.arguments.items():
            arg.value = getattr(self._parsed, name, arg.default)
        self._unparsed = []
        for term in unparsed:
            self._unparsed += split_input(' \'%s\' ' % term)
        self._parser_modified = False
