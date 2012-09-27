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

from kamaki.cli import command#, set_api_description
#set_api_description('config', 'Configuration commands')
API_DESCRIPTION = {'config':'Configuration commands'}

@command()
class config_list(object):
    """List configuration options"""

    def update_parser(self, parser):
        parser.add_argument('-a', dest='all', action='store_true',
                          default=False, help='include default values')

    def main(self):
        include_defaults = self.args.all
        for section in sorted(self.config.sections()):
            items = self.config.items(section, include_defaults)
            for key, val in sorted(items):
                print('%s.%s = %s' % (section, key, val))

@command()
class config_get(object):
    """Show a configuration option"""

    def main(self, option):
        section, sep, key = option.rpartition('.')
        section = section or 'global'
        value = self.config.get(section, key)
        if value is not None:
            print(value)

@command()
class config_set(object):
    """Set a configuration option"""

    def main(self, option, value):
        section, sep, key = option.rpartition('.')
        section = section or 'globail'
        self.config.set(section, key, value)
        self.config.write()

@command()
class config_delete(object):
    """Delete a configuration option (and use the default value)"""

    def main(self, option):
        section, sep, key = option.rpartition('.')
        section = section or 'global'
        self.config.remove_option(section, key)
        self.config.write()
