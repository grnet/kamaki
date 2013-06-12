# Copyright 2012 GRNET S.A. All rights reserved.
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

try:
    from progress.bar import ShadyBar as KamakiProgressBar
except ImportError:
    try:
        from progress.bar import Bar as KamakiProgressBar
    except ImportError:
        pass
    # progress not installed - pls, pip install progress
    pass

log = getLogger(__name__)


class Argument(object):
    """An argument that can be parsed from command line or otherwise.
    This is the general Argument class. It is suggested to extent this
    class into more specific argument types.
    """

    def __init__(self, arity, help=None, parsed_name=None, default=None):
        self.arity = int(arity)

        if help:
            self.help = help
        if parsed_name:
            self.parsed_name = parsed_name
        self.default = default

    @property
    def parsed_name(self):
        """the string which will be recognised by the parser as an instance
            of this argument
        """
        return getattr(self, '_parsed_name', None)

    @parsed_name.setter
    def parsed_name(self, newname):
        self._parsed_name = getattr(self, '_parsed_name', [])
        if isinstance(newname, list) or isinstance(newname, tuple):
            self._parsed_name += list(newname)
        else:
            self._parsed_name.append('%s' % newname)

    @property
    def help(self):
        """a user friendly help message"""
        return getattr(self, '_help', None)

    @help.setter
    def help(self, newhelp):
        self._help = '%s' % newhelp

    @property
    def arity(self):
        """negative for repeating, 0 for flag, 1 or more for values"""
        return getattr(self, '_arity', None)

    @arity.setter
    def arity(self, newarity):
        newarity = int(newarity)
        self._arity = newarity

    @property
    def default(self):
        """the value of this argument when not set"""
        if not hasattr(self, '_default'):
            self._default = False if self.arity == 0 else None
        return self._default

    @default.setter
    def default(self, newdefault):
        self._default = newdefault

    @property
    def value(self):
        """the value of the argument"""
        return getattr(self, '_value', self.default)

    @value.setter
    def value(self, newvalue):
        self._value = newvalue

    def update_parser(self, parser, name):
        """Update argument parser with self info"""
        action = 'append' if self.arity < 0\
            else 'store_true' if self.arity == 0\
            else 'store'
        parser.add_argument(
            *self.parsed_name,
            dest=name,
            action=action,
            default=self.default,
            help=self.help)

    def main(self):
        """Overide this method to give functionality to your args"""
        raise NotImplementedError


class ConfigArgument(Argument):
    """Manage a kamaki configuration (file)"""

    _config_file = None

    @property
    def value(self):
        """A Config object"""
        super(self.__class__, self).value
        return super(self.__class__, self).value

    @value.setter
    def value(self, config_file):
        if config_file:
            self._value = Config(config_file)
            self._config_file = config_file
        elif self._config_file:
            self._value = Config(self._config_file)
        else:
            self._value = Config()

    def get(self, group, term):
        """Get a configuration setting from the Config object"""
        return self.value.get(group, term)

    def get_groups(self):
        suffix = '_cli'
        slen = len(suffix)
        return [term[:-slen] for term in self.value.keys('global') if (
            term.endswith(suffix))]

    def get_cli_specs(self):
        suffix = '_cli'
        slen = len(suffix)
        return [(k[:-slen], v) for k, v in self.value.items('global') if (
            k.endswith(suffix))]

    def get_global(self, option):
        return self.value.get_global(option)

    def get_cloud(self, cloud, option):
        return self.value.get_cloud(cloud, option)

_config_arg = ConfigArgument(
    1, 'Path to configuration file', ('-c', '--config'))


class CmdLineConfigArgument(Argument):
    """Set a run-time setting option (not persistent)"""

    def __init__(self, config_arg, help='', parsed_name=None, default=None):
        super(self.__class__, self).__init__(1, help, parsed_name, default)
        self._config_arg = config_arg

    @property
    def value(self):
        """A key=val option"""
        return super(self.__class__, self).value

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


class IntArgument(ValueArgument):

    @property
    def value(self):
        """integer (type checking)"""
        return getattr(self, '_value', self.default)

    @value.setter
    def value(self, newvalue):
        if newvalue == self.default:
            self._value = self.default
            return
        try:
            self._value = int(newvalue)
        except ValueError:
            raiseCLIError(CLISyntaxError(
                'IntArgument Error',
                details=['Value %s not an int' % newvalue]))


class DateArgument(ValueArgument):
    """
    :value type: a string formated in an acceptable date format

    :value returns: same date in first of DATE_FORMATS
    """

    DATE_FORMATS = [
        "%a %b %d %H:%M:%S %Y",
        "%A, %d-%b-%y %H:%M:%S GMT",
        "%a, %d %b %Y %H:%M:%S GMT"]

    INPUT_FORMATS = DATE_FORMATS + ["%d-%m-%Y", "%H:%M:%S %d-%m-%Y"]

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

    @value.setter
    def value(self, newvalue):
        if newvalue:
            self._value = self.format_date(newvalue)

    def format_date(self, datestr):
        for format in self.INPUT_FORMATS:
            try:
                t = dtm.strptime(datestr, format)
            except ValueError:
                continue
            return t  # .strftime(self.DATE_FORMATS[0])
        raiseCLIError(
            None,
            'Date Argument Error',
            details='%s not a valid date. correct formats:\n\t%s' % (
                datestr, self.INPUT_FORMATS))


class VersionArgument(FlagArgument):
    """A flag argument with that prints current version"""

    @property
    def value(self):
        """bool"""
        return super(self.__class__, self).value

    @value.setter
    def value(self, newvalue):
        self._value = newvalue
        self.main()

    def main(self):
        """Print current version"""
        if self.value:
            import kamaki
            print('kamaki %s' % kamaki.__version__)


class KeyValueArgument(Argument):
    """A Value Argument that can be repeated

    :syntax: --<arg> key1=value1 --<arg> key2=value2 ...
    """

    def __init__(self, help='', parsed_name=None, default=[]):
        super(KeyValueArgument, self).__init__(-1, help, parsed_name, default)

    @property
    def value(self):
        """
        :input: key=value
        :output: {'key1':'value1', 'key2':'value2', ...}
        """
        return super(KeyValueArgument, self).value

    @value.setter
    def value(self, keyvalue_pairs):
        self._value = {}
        for pair in keyvalue_pairs:
            key, sep, val = pair.partition('=')
            if not sep:
                raiseCLIError(
                    CLISyntaxError('Argument syntax error '),
                    details='%s is missing a "=" (usage: key1=val1 )\n' % pair)
            self._value[key.strip()] = val.strip()


class ProgressBarArgument(FlagArgument):
    """Manage a progress bar"""

    def __init__(self, help='', parsed_name='', default=True):
        self.suffix = '%(percent)d%%'
        super(ProgressBarArgument, self).__init__(help, parsed_name, default)
        try:
            KamakiProgressBar
        except NameError:
            log.warning('WARNING: no progress bar functionality')

    def clone(self):
        """Get a modifiable copy of this bar"""
        newarg = ProgressBarArgument(
            self.help,
            self.parsed_name,
            self.default)
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
    options=CmdLineConfigArgument(
        _config_arg, 'Override a config value', ('-o', '--options'))
)


#  Initial command line interface arguments


class ArgumentParseManager(object):
    """Manage (initialize and update) an ArgumentParser object"""

    parser = None
    _arguments = {}
    _parser_modified = False
    _parsed = None
    _unparsed = None

    def __init__(self, exe, arguments=None):
        """
        :param exe: (str) the basic command (e.g. 'kamaki')

        :param arguments: (dict) if given, overrides the global _argument as
            the parsers arguments specification
        """
        self.parser = ArgumentParser(
            add_help=False,
            formatter_class=RawDescriptionHelpFormatter)
        self.syntax = '%s <cmd_group> [<cmd_subbroup> ...] <cmd>' % exe
        if arguments:
            self.arguments = arguments
        else:
            global _arguments
            self.arguments = _arguments
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
        """(dict) arguments the parser should be aware of"""
        return self._arguments

    @arguments.setter
    def arguments(self, new_arguments):
        if new_arguments:
            assert isinstance(new_arguments, dict)
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
        if not arguments:
            arguments = self._arguments

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
        """Do parse user input"""
        try:
            if new_args:
                self._parsed, unparsed = self.parser.parse_known_args(new_args)
            else:
                self._parsed, unparsed = self.parser.parse_known_args()
        except SystemExit:
            # deal with the fact that argparse error system is STUPID
            raiseCLIError(CLISyntaxError('Argument Syntax Error'))
        for name, arg in self.arguments.items():
            arg.value = getattr(self._parsed, name, arg.default)
        self._unparsed = []
        for term in unparsed:
            self._unparsed += split_input(' \'%s\' ' % term)
        self._parser_modified = False
