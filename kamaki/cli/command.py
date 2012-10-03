# Copyright 2011 GRNET S.A. All rights reserved.
#
# Redistribution and use in source and binary forms, with or
# without modification, are permitted provided that the following
# conditions are met:
#
#   1. Redistributions of source code must retain the above
#	  copyright notice, this list of conditions and the following
#	  disclaimer.
#
#   2. Redistributions in binary form must reproduce the above
#	  copyright notice, this list of conditions and the following
#	  disclaimer in the documentation and/or other materials
#	  provided with the distribution.
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

import cmd

class Command(object):
	"""Store a command and the next-level commands as well - no deep tree here"""
	_name = None
	path = None
	cmd_class = None
	subcommands = {}
	help = ' '

	def __init__(self, path, help = ' ', subcommands={}, cmd_class=None):
		self.path = path
		self.help = help
		self.subcommands =dict(subcommands)
		self.cmd_class = cmd_class

	@property 
	def name(self):
		if self._name is None:
			self._name = self.path.split('_')[-1]
		return str(self._name)

	def add_subcmd(self, subcmd):
		if subcmd.path == self.path+'_'+subcmd.name:
			self.subcommands[subcmd.name] = subcmd
			return True
		return False
	def get_subcmd(self, name):
		try:
			return self.subcommands[name]
		except KeyError:
			return None

	def contains(self, name):
		"""Check if a name is a direct child of self"""
		return self.subcommands.has_key(name)

	def is_command(self):
		return self.cmd_class is not None

	def set_class(self, cmd_class):
		self.cmd_class = cmd_class
	def get_class(self):
		return self.cmd_class

	def get_subnames(self):
		return self.subcommands.keys()
	def get_subcommands(self):
		return self.subcommands.values()
	def sublen(self):
		return len(self.subcommands)

	def pretty_print(self, recursive=False):
		print('Path: %s (Name: %s) is_cmd: %s\n\thelp: %s'%(self.path, self.name,
			self.is_command(), self.help))
		for cmd in self.get_subcommands():
			cmd.pretty_print(recursive)

def test_Command():
	cmd = Command('store', 'A store thingy')
	cmd.add_subcmd(Command('store_list'))
	tmp = cmd.get_subcmd('list')
	tmp.add_subcmd(Command('store_list_all', 'List everything'))
	tmp.add_subcmd(Command('store_list_one', 'List just one stuff'))
	cmd.pretty_print(True)

class Shell(cmd.Cmd):
	"""Simple command processor example."""

	def do_greet(self, line):
		"""Hello [cmd]
			@line some line"""
		print "hello"

	def do_lala(self, lala):
		print('This is what I got: %s'%lala)
	def help_lala(self):
		print('This is SPAAARTAAAAAAA')

	def do_lalum(self, args):
		print('lalum')
	def complete_lalum(self, text, line, begidx, endidx):
		completions = ['lala']
		return completions

	def do_EOF(self, line):
		return True

#sh = Shell()
#sh.prompt = 'lala_$ '
#sh.cmdloop()

#import sys
#sh.onecmd(' '.join(sys.argv[1:]))
test_Command()