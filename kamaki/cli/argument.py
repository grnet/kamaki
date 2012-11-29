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
from kamaki.cli.errors import CLISyntaxError
from kamaki.cli.utils import split_input

from argparse import ArgumentParser, ArgumentError

try:
    from progress.bar import IncrementalBar
except ImportError:
    # progress not installed - pls, pip install progress
    pass


class Argument(object):
    """An argument that can be parsed from command line or otherwise.
    This is the general Argument class. It is suggested to extent this
    class into more specific argument types.
    """

    def __init__(self, arity, help=None, parsed_name=None, default=None):
        if help is not None:
            self.help = help
        if parsed_name is not None:
            self.parsed_name = parsed_name
        if default is not None:
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
            self._parsed_name.append(unicode(newname))

    @property
    def help(self):
        """a user friendly help message"""
        return getattr(self, '_help', None)

    @help.setter
    def help(self, newhelp):
        self._help = unicode(newhelp)

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
        parser.add_argument(*self.parsed_name, dest=name, action=action,
            default=self.default, help=self.help)

    def main(self):
        """Overide this method to give functionality to your args"""
        raise NotImplementedError


class ConfigArgument(Argument):
    """Manage a kamaki configuration file"""

    _config_file = None
    """The configuration file"""

    @property
    def value(self):
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
        return self.value.get(group, term)

    def get_groups(self):
        return self.value.apis()

_config_arg = ConfigArgument(1, 'Path to configuration file', '--config')


class CmdLineConfigArgument(Argument):
    """Set a run-time setting option (not persistent)"""

    def __init__(self, config_arg, help='', parsed_name=None, default=None):
        super(self.__class__, self).__init__(1, help, parsed_name, default)
        self._config_arg = config_arg

    @property
    def value(self):
        return super(self.__class__, self).value

    @value.setter
    def value(self, options):
        if options == self.default:
            return
        if not isinstance(options, list):
            options = [unicode(options)]
        for option in options:
            keypath, sep, val = option.partition('=')
            if not sep:
                raise CLISyntaxError('Argument Syntax Error ',
                    details='%s is missing a "=" (usage: -o section.key=val)'\
                        % option)
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
    :value type: accepts no values from user
    :value returns: true if argument is set, false otherwise
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


class IntArgument(ValueArgument):
    """
    :value type: integer (type checking occurs)
    :value returns: an integer
    """

    @property
    def value(self):
        return getattr(self, '_value', self.default)

    @value.setter
    def value(self, newvalue):
        if newvalue == self.default:
            self._value = self.default
            return
        try:
            self._value = int(newvalue)
        except ValueError:
            raise CLISyntaxError('IntArgument Error',
                details='Value %s not an int' % newvalue)


class VersionArgument(FlagArgument):
    """A flag argument with that prints current version"""

    @property
    def value(self):
        return super(self.__class__, self).value

    @value.setter
    def value(self, newvalue):
        self._value = newvalue
        self.main()

    def main(self):
        if self.value:
            import kamaki
            print('kamaki %s' % kamaki.__version__)


class KeyValueArgument(Argument):
    """A Value Argument that can be repeated

    --<argument> key1=value1 --<argument> key2=value2 ...
    """

    def __init__(self, help='', parsed_name=None, default=[]):
        super(KeyValueArgument, self).__init__(-1, help, parsed_name, default)

    @property
    def value(self):
        return super(KeyValueArgument, self).value

    @value.setter
    def value(self, keyvalue_pairs):
        self._value = {}
        for pair in keyvalue_pairs:
            key, sep, val = pair.partition('=')
            if not sep:
                raise CLISyntaxError('Argument syntax error ',
                    details='%s is missing a "=" (usage: key1=val1 )\n' % pair)
            self._value[key.strip()] = val.strip()


class ProgressBarArgument(FlagArgument):

    def __init__(self, help='', parsed_name='', default=True):
        self.suffix = '%(percent)d%%'
        super(ProgressBarArgument, self).__init__(help, parsed_name, default)
        try:
            IncrementalBar
        except NameError:
            print('Waring: no progress bar functionality')

    def clone(self):
        newarg = ProgressBarArgument(
            self.help,
            self.parsed_name,
            self.default)
        newarg._value = self._value
        return newarg

    def get_generator(self, message, message_len=25):
        if self.value:
            return None
        try:
            self.bar = IncrementalBar()
        except NameError:
            self.value = None
            return self.value
        self.bar.message = message.ljust(message_len)
        self.bar.suffix = '%(percent)d%% - %(eta)ds'

        def progress_gen(n):
            for i in self.bar.iter(range(int(n))):
                yield
            yield
        return progress_gen

    def finish(self):
        if self.value:
            return
        mybar = getattr(self, 'bar', None)
        if mybar:
            mybar.finish()


_arguments = dict(config=_config_arg,
    help=Argument(0, 'Show help message', ('-h', '--help')),
    debug=FlagArgument('Include debug output', ('-d', '--debug')),
    include=FlagArgument('Include protocol headers in the output',
        ('-i', '--include')),
    silent=FlagArgument('Do not output anything', ('-s', '--silent')),
    verbose=FlagArgument('More info at response', ('-v', '--verbose')),
    version=VersionArgument('Print current version', ('-V', '--version')),
    options=CmdLineConfigArgument(_config_arg,
        'Override a config value',
        ('-o', '--options'))
)


def parse_known_args(parser, arguments=None):
    parsed, unparsed = parser.parse_known_args()
    for name, arg in arguments.items():
        arg.value = getattr(parsed, name, arg.default)
    newparsed = []
    for term in unparsed:
        newparsed += split_input(' \'%s\' ' % term)
    return parsed, newparsed


def init_parser(exe, arguments):
    parser = ArgumentParser(add_help=False)
    parser.prog = '%s <cmd_group> [<cmd_subbroup> ...] <cmd>' % exe
    update_arguments(parser, arguments)
    return parser


def update_arguments(parser, arguments):
    for name, argument in arguments.items():
        try:
            argument.update_parser(parser, name)
        except ArgumentError:
            pass
