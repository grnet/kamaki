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

from kamaki.cli.commands import errors
from kamaki.cli import command
from kamaki.cli.commands import _command_init
from kamaki.cli.command_tree import CommandTree
from kamaki.clients import livetest
from kamaki.cli.errors import raiseCLIError

livetest_cmds = CommandTree('livetest', 'Client func. tests on live servers')
_commands = [livetest_cmds]


class _livetest_init(_command_init):

    def _run(self, client, method=None):
        if method:
            livetest.main([client, method], config=self.config)
        else:
            livetest.main([client], config=self.config)

    def main(self, client, method=None):
        return self._run(client, method)


@command(livetest_cmds)
class livetest_error(_livetest_init):
    """Create an error message with optional message"""

    @errors.generic.all
    def _run(self, errmsg='', importance=0, index=0):
        l = [1, 2]
        try:
            l[int(index)]
        except Exception as err:
            raiseCLIError(err, errmsg, importance)
        raiseCLIError(None, errmsg, importance)

    def main(self, errmsg='', importance=0, index=0):
        self._run(errmsg, importance, index)


@command(livetest_cmds)
class livetest_args(_livetest_init):
    """Test how arguments are treated by kamaki"""

    @errors.generic.all
    def _run(self, *args):
        self.writeln(args)

    def main(self, *args):
        self._run(args)


@command(livetest_cmds)
class livetest_all(_livetest_init):
    """test all clients"""

    @errors.generic.all
    def _run(self):
        for client in ('pithos', 'cyclades', 'image', 'astakos'):
            super(self.__class__, self)._run(client)

    def main(self):
        self._run()


@command(livetest_cmds)
class livetest_pithos(_livetest_init):
    """ test Pithos client"""

    @errors.generic.all
    def _run(self, method=None):
        super(self.__class__, self)._run('pithos', method)

    def main(self, method=None):
        self._run(method)


@command(livetest_cmds)
class livetest_cyclades(_livetest_init):
    """ test Cyclades client"""

    @errors.generic.all
    def _run(self, method=None):
        super(self.__class__, self)._run('cyclades', method)

    def main(self, method=None):
        self._run(method)


@command(livetest_cmds)
class livetest_image(_livetest_init):
    """ test Image client"""

    @errors.generic.all
    def _run(self, method=None):
        super(self.__class__, self)._run('image', method)

    def main(self, method=None):
        self._run(method)


@command(livetest_cmds)
class livetest_astakos(_livetest_init):
    """ test Astakos client"""

    @errors.generic.all
    def _run(self, method=None):
        super(self.__class__, self)._run('astakos', method)

    def main(self, method=None):
        self._run(method)


@command(livetest_cmds)
class livetest_prints(_livetest_init):
    """ user-test print methods for lists and dicts"""

    d1 = {'key0a': 'val0a', 'key0b': 'val0b', 'key0c': 'val0c'}

    l1 = [1, 'string', '3', 'many (2 or 3) numbers and strings combined', 5]

    d2 = {'id': 'val0a', 'key0b': d1, 'title': l1}

    l2 = [d2, l1, d1]

    spr_msg = 'long key of size 75 characters is used to check the effects on'
    spr_msg += ' total result for long messages that drive pep8 completely mad'
    d3 = {'dict 1': d1, 'dict 2': d2, 'list2': l2, spr_msg: l1}

    @errors.generic.all
    def _run(self):
        from kamaki.cli.utils import print_dict, print_list, print_items
        self.writeln('Test simple dict:\n- - -')
        print_dict(self.d1)
        self.writeln('- - -\n')
        self.writeln('\nTest simple list:\n- - -')
        print_list(self.l1)
        self.writeln('- - -\n')
        self.writeln('\nTest 2-level dict:\n- - -')
        print_dict(self.d2)
        self.writeln('- - -\n')
        self.writeln('\nTest non-trivial list:\n- - -')
        print_list(self.l2)
        self.writeln('- - -')
        self.writeln('\nTest extreme dict:\n- - -')
        print_dict(self.d3)
        self.writeln('- - -\n')
        self.writeln('Test simple enumerated dict:\n- - -')
        print_dict(self.d1, with_enumeration=True)
        self.writeln('- - -\n')
        self.writeln('\nTest simple enumerated list:\n- - -')
        print_list(self.l1, with_enumeration=True)
        self.writeln('- - -\n')
        self.writeln('Test non-trivial deep-enumerated dict:\n- - -')
        print_dict(self.d2, with_enumeration=True, recursive_enumeration=True)
        self.writeln('- - -\n')
        self.writeln('\nTest non-trivial enumerated list:\n- - -')
        print_list(self.l2, with_enumeration=True)
        self.writeln('- - -\n')
        self.writeln('\nTest print_items with id:\n- - -')
        print_items([
            {'id': '42', 'title': 'lalakis 1', 'content': self.d1},
            {'id': '142', 'title': 'lalakis 2', 'content': self.d2}])
        self.writeln('- - -')
        self.writeln('\nTest print_items with id and enumeration:\n- - -')
        print_items(
            [
                {'id': '42', 'title': 'lalakis 1', 'content': self.d1},
                {'id': '142', 'title': 'lalakis 2', 'content': self.d2}],
            with_enumeration=True)
        self.writeln('- - -')
        self.writeln('\nTest print_items with id, title, redundancy:\n- - -')
        print_items(
            [
                {'id': '42', 'title': 'lalakis 1', 'content': self.d1},
                {'id': '142', 'title': 'lalakis 2', 'content': self.d2}],
            title=('id', 'title'),
            with_redundancy=True)
        self.writeln('- - -')
        self.writeln('\nTest print_items with lists- - -')
        print_items([['i00', 'i01', 'i02'], [self.l2, 'i11', self.d1], 3])
        self.writeln('- - -')

    def main(self):
        self._run()
