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
# USE, DATA, OR PROFITS; OR BUSINESS INTERaUPTION) HOWEVER CAUSED
# AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN
# ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# The views and conclusions contained in the software and
# documentation are those of the authors and should not be
# interpreted as representing official policies, either expressed
# or implied, of GRNET S.A.

from kamaki.cli import command
from kamaki.cli.argument import FlagArgument
from kamaki.cli.commands import _command_init, errors
from kamaki.cli.command_tree import CommandTree

config_cmds = CommandTree('config', 'Kamaki configurations')
_commands = [config_cmds]

about_options = '\nAbout options:\
    \n. syntax: [group.]option\
    \n. example: file.account\
    \n. special case: <option> is equivalent to global.<option>\
    \n. configuration file syntax:\
    \n.   [group]\
    \n.   option=value\
    \n.   (more options can be set per group)'


@command(config_cmds)
class config_list(_command_init):
    """List all configuration options
    FAQ:
    Q: I haven't set any options!
    A: Defaults are used (override with /config set )
    Q: There are more options than I have set
    A: Default options remain if not explicitly replaced or deleted
    """

    @errors.generic.all
    def _run(self):
        for section in sorted(self.config.sections()):
            items = self.config.items(section)
            for key, val in sorted(items):
                print('%s.%s = %s' % (section, key, val))

    def main(self):
        self._run()


@command(config_cmds)
class config_get(_command_init):
    """Show a configuration option"""

    __doc__ += about_options

    @errors.generic.all
    def _run(self, option):
        section, sep, key = option.rpartition('.')
        section = section or 'global'
        value = self.config.get(section, key)
        if value:
            print(value)

    def main(self, option):
        self._run(option)


@command(config_cmds)
class config_set(_command_init):
    """Set a configuration option"""

    __doc__ += about_options

    @errors.generic.all
    def _run(self, option, value):
        section, sep, key = option.rpartition('.')
        section = section or 'global'
        self.config.set(section, key, value)
        self.config.write()
        self.config.reload()

    def main(self, option, value):
        self._run(option, value)


@command(config_cmds)
class config_delete(_command_init):
    """Delete a configuration option
    Default values are not removed by default. To alter this behavior in a
    session, use --default.
    """

    arguments = dict(
        default=FlagArgument(
            'Remove default value as well (persists until end of session)',
            '--default')
    )

    @errors.generic.all
    def _run(self, option):
        section, sep, key = option.rpartition('.')
        section = section or 'global'
        self.config.remove_option(section, key, self['default'])
        self.config.write()
        self.config.reload()

    def main(self, option):
        self._run(option)
