# Copyright 2012 GRNET S.A. All rights reserved.
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

from kamaki.cli.commands import _command_init
from kamaki.cli import command
from kamaki.cli.command_tree import CommandTree
from kamaki.cli.errors import CLIError
from kamaki.clients.commissioning import CanonifyException


class commissioning_cli(object):

    api_spec = None
    appname = None
    client = None
    add_context = False
    ctree = None
    description = None

    def __init__(self):
        self.api_spec = self.client.api_spec
        self.appname = self.client.appname
        self.ctree = CommandTree(self.appname, self.description)

    def generate_all(self):
        for f in self.api_spec.call_names():
            c = self.mkClass(f)
            command(self.ctree)(c)

    def mkClass(self, method):
        class C(_command_init):

            __doc__ = self.api_spec.get_doc(method)

            def init(this):
                this.token = (this.config.get(self.appname, 'token') or
                              this.config.get('global', 'token'))
                this.base_url = (this.config.get(self.appname, 'url') or
                                 this.config.get('global', 'url'))
                this.client = self.client(this.base_url, this.token)

            def call(this, method, args):
                ctx = '=null ' if self.add_context else ''
                arglist = '[' + ctx + ' '.join(args) + ']'
                argdict = self.api_spec.parse(method, arglist)
                f = getattr(this.client, method)
                return f(**argdict)

            def main(this, *args):
                this.init()
                try:
                    r = this.call(method, args)
                    print r
                except CanonifyException, e:
                    params = self.api_spec.show_input_canonical(method)
                    meth = method.replace('_', ' ')
                    m = '%s\n  usage: %s %s' % (e, meth, params)
                    raise CLIError('%s: %s\n' % (self.appname, m))
                except Exception as e:
                    raise CLIError('%s: %s\n' % (self.appname, e))

        C.__name__ = self.appname + '_' + method
        return C
