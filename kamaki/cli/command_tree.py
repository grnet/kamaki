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
#from .errors import CLIUnknownCommand, CLICmdIncompleteError, CLICmdSpecError, CLIError

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

	@property 
	def is_command(self):
		return self.cmd_class is not None
	@property 
	def has_description(self):
		return len(self.help.strip()) > 0
	@property 
	def description(self):
		return self.help

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
			self.is_command, self.help))
		for cmd in self.get_subcommands():
			cmd.pretty_print(recursive)

def test_Command():
	cmd = Command('store', 'A store thingy')
	cmd.add_subcmd(Command('store_list'))
	tmp = cmd.get_subcmd('list')
	tmp.add_subcmd(Command('store_list_all', 'List everything'))
	tmp.add_subcmd(Command('store_list_one', 'List just one stuff'))
	cmd.pretty_print(True)

class CommandTree(object):

	groups = {}
	_all_commands = {}
	name = None
	description = None

	def __init__(self, name, description=''):
		self.name = name
		self.description = description

	def add_command(self, command_path, description=None, cmd_class=None):
		terms = command_path.split('_')
		try:
			cmd = self.groups[terms[0]]
		except KeyError:
			cmd = Command(terms[0])
			self.groups[terms[0]] = cmd
			self._all_commands[terms[0]] = cmd
		path = terms[0]
		for term in terms[1:]:
			path += '_'+term
			try:
				cmd = cmd.subcommands[term]
			except KeyError:
				new_cmd = Command(path)
				self._all_commands[path] = new_cmd
				cmd.add_subcmd(new_cmd)
				cmd = new_cmd
		if cmd_class is not None:
			cmd.set_class(cmd_class)
		if description is not None:
			cmd.help = description
	def get_command(self, path):
		return self._all_commands[path]
	def get_groups(self):
		return self.groups.values()
	def get_group_names(self):
		return self.groups.keys()

	def set_description(self, path, description):
		self._all_commands[path].help = description
	def get_descitpion(self, path):
		return self._all_commands[path].help
	def set_class(self, path, cmd_class):
		self._all_commands[path].set_class(cmd_class)
	def get_class(self, path):
		return self._all_commands[path].get_class()

	def get_subnames(self, path):
		return self._all_commands[path].get_subnames()
	def get_subcommands(self, path):
		return self._all_commands[path].get_subcommands()
	def get_parent(self, path):
		if '_' not in path:
			return None
		terms = path.split('_')
		parent_path = '_'.join(terms[:-1])
		return self._all_commands[parent_path]
	def get_closest_ancestor_command(self, path):
		path, sep, name = path.rpartition('_')
		while len(path) > 0:
			cmd = self._all_commands[path]
			if cmd.is_command:
				return cmd
			path, sep, name = path.rpartition('_')
		return None

		if '_' not in path:
			return None
		terms = terms[:-1]
		while len(terms) > 0:
			tmp_path = '_'.join(terms)
			cmd = self._all_commands[tmp_path]
			if cmd.is_command:
				return cmd
			terms = terms[:-1]
		raise KeyError('No ancestor commands')

	def pretty_print(self, group=None):
		if group is None:
			for group in self.groups:
				self.pretty_print(group)
		else:
			self.groups[group].pretty_print(recursive=True)

def test_CommandTree():
	tree = CommandTree('kamaki', 'the kamaki tools')
	tree.add_command('store', 'A storage thingy')
	tree.add_command('server_list_lala', description='A testing server list', cmd_class=Shell)
	tree.add_command('store_list_all', 'List all things', cmd_class=Command)
	tree.add_command('store_list', 'List smthing pls', cmd_class=Shell)
	tree.add_command('server_list', description='A server list subgrp')
	tree.add_command('server', description='A server is a SERVER', cmd_class=CommandTree)
	tree.set_class('server', None)
	tree.set_description('server_list', '')
	if tree.get_class('server_list_lala') is Shell:
		print('server_list_lala is Shell')
	else:
		print('server_list_lala is not Shell')
	tree.pretty_print()
	print('store_list_all closest parent command is %s'%tree.get_closest_ancestor_command('store_list_all').path)
	tree.set_class('store', tree.get_command('store_list').get_class())
	tree.set_class('store_list', None)
	print('store_list_all closest parent command is %s'%tree.get_closest_ancestor_command('store_list_all').path)
	try:
		print('nonexisting_list_command closest parent is %s'%tree.get_closest_ancestor_command('nonexisting_list_command').path)
	except KeyError:
		print('Aparrently nonexisting_list_command is nonexisting ')

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

if __name__ == '__main__':
	sh = Shell()
	sh.prompt = 'lala_$ '
	sh.cmdloop()

	#import sys
	#sh.onecmd(' '.join(sys.argv[1:]))
	#test_CommandTree()