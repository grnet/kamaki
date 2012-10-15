# Copyright 2012 GRNET S.A. All rights reserved.
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

from cmd import Cmd
from new import instancemethod
from os import popen
from argparse import ArgumentParser
from . import _update_parser
from .errors import CLIError
from .argument import _arguments
from .utils import magenta

def _fix_arguments():
	_arguments.pop('version', None)
	_arguments.pop('options', None)

class Shell(Cmd):
	"""Kamaki interactive shell"""
	_prefix = '['
	_suffix = ']:'

	def greet(self, version):
		print('kamaki v%s - Interactive Shell\n\t(exit or ^D to exit)\n'%version)
	def set_prompt(self, new_prompt):
		self.prompt = '[%s]:'%new_prompt

	def do_exit(self, line):
		print
		return True

	def do_shell(self, line):
		output = popen(line).read()
		print output
	def help_shell(self):
		print('Execute OS shell commands')

	@classmethod
	def _register_method(self, method, name):
		#self.__dict__[name] = method
		self._tmp_method = instancemethod(method, name, self)
		setattr(self, name, self._tmp_method)
		del self._tmp_method

	def _register_command(self, cmd):
		method_name = 'do_%s'%cmd.name
		def do_method(self, line):
			subcmd, cmd_argv = cmd.parse_out(line.split())

			subname = subcmd.name if cmd == subcmd else subcmd.path
			cmd_parser = ArgumentParser(subname, add_help=False)
			if subcmd.is_command:
				cls = subcmd.get_class()
				instance = cls(_arguments)
				_update_parser(cmd_parser, instance.arguments)
				cmd_parser.prog += ' '+cls.syntax
			if '-h' in cmd_argv or '--help'in cmd_argv:
				cmd_parser.description = subcmd.help
				cmd_parser.print_help()
				return

			if subcmd.is_command:
				parsed, unparsed = cmd_parser.parse_known_args(cmd_argv)

				for name, arg in instance.arguments.items():
					arg.value = getattr(parsed, name, arg.default)
				try:
					instance.main(*unparsed)
				except TypeError as e:
					if e.args and e.args[0].startswith('main()'):
						print(magenta('Syntax error'))
						if instance.get_argument('verbose'):
							print(unicode(e))
						print(subcmd.description)
						cmd_parser.print_help()
					else:
						raise
				except CLIError as err:
					_print_error_message(err)
			else:
				newshell = Shell()
				newshell.set_prompt(' '.join(cmd.path.split('_')))
				newshell.do_EOF = newshell.do_exit
				newshell.kamaki_loop(cmd, cmd.path)
		self._register_method(do_method, method_name)

		method_name = 'help_%s'%cmd.name
		def help_method(self):
			if cmd.has_description:
				print(cmd.description)
			else:
				print('(no description)')
		self._register_method(help_method, method_name)

		method_name = 'complete_%s'%cmd.name
		def complete_method(self, text, line, begidx, endidx):
			print('Complete 0% FAT')
			return cmd.get_subnames()
		self._register_method(complete_method, method_name)
		print('Registed %s as %s'%(complete_method, method_name))

	def kamaki_loop(self,command,prefix=''):
		#setup prompt
		if prefix in (None, ''):
			self.set_prompt(command.name)
		else:
			self.set_prompt(' '.join(command.path.split()))

		for cmd in command.get_subcommands():
			self._register_command(cmd)

		self.cmdloop()