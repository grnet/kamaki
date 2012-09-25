#A. One-command CLI
#	1. Get a command string 		DONE
#	2. Parse out some Arguments 	DONE
#		a. We need an Argument "library" for each command-level 	DONE
#		b. Handle arg errors 	
#	3. Retrieve and validate command_sequence
#		a. For faster responses, first command can be chosen from
#			a prefixed list of names, loaded from the config file
#		b. Normally, each 1st level command has a file to read
#			command specs from. Load command_specs in this file
#			i. A dict with command specs is created
#				e.g. {'store':{'list':{'all', None}, 'info'}, 'server':{'list', 'info'}}
#				but in this case there will be only 'store', or 'server', etc.
#		c. Now, loop over the other parsed terms and check them against the commands
#			i. That will produce a path of the form ['store', 'list' 'all']
#		d. Catch syntax errors
#	4. Instaciate object to exec
#		a. For path ['store', 'list', 'all'] instatiate store_list_all()
#	5. Parse out some more Arguments 
#		a. Each command path has an "Argument library" to check your args against
#	6. Call object.main() and catch ClientErrors
#		a. Now, there are some command-level syntax errors that we should catch
#			as syntax errors? Maybe! Why not?

#Shell
#	1. Load ALL available command specs in advance
#	2. Iimport cmd (and run it ?)
#	3. There is probably a way to tell cmd of the command paths you support.
#	4. If cmd does not support it, for the sellected path call parse out stuff
#		as in One-command
#	5. Instatiate, parse_out and run object like in One-command
#	6. Run object.main() . Again, catch ClientErrors and, probably, syntax errors
import gevent.monkey
#Monkey-patch everything for gevent early on
gevent.monkey.patch_all()

from sys import argv, exit

from inspect import getargspec
from os.path import basename
from argparse import ArgumentParser

from .utils import CommandTree, Argument
from .config import Config
from .errors import CLIError, CLISyntaxError

try:
	from colors import magenta, red, yellow, bold
except ImportError:
	#No colours? No worries, use dummy foo instead
	def bold(val):
		return val
	red = yellow = magenta = bold

_commands = CommandTree()

class VersionArgument(Argument):
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
			print('kamaki %s'%kamaki.__version__)
			self._exit(0)

	def _exit(self, num):
			pass

class ConfigArgument(Argument):
	@property 
	def value(self):
		return super(self.__class__, self).value
	@value.setter
	def value(self, config_file):
		self._value = Config(config_file) if config_file is not None else Config()

class CmdLineConfigArgument(Argument):
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
		options = [unicode(options)] if not isinstance(options, list) else options
		for option in options:
			keypath, sep, val = option.partition('=')
			if not sep:
				raise CLISyntaxError(details='Missing = between key and value: -o section.key=val')
			section, sep, key = keypath.partition('.')
			if not sep:
				raise CLISyntaxError(details='Missing . between section and key: -o section.key=val')
		self._config_arg.value.override(section.strip(), key.strip(), val.strip())

_config_arg = ConfigArgument(1, 'Path to configuration file', '--config')
_arguments = dict(config = _config_arg,
	debug = Argument(0, 'Include debug output', ('-d', '--debug')),
	include = Argument(0, 'Include protocol headers in the output', ('-i', '--include')),
	silent = Argument(0, 'Do not output anything', ('-s', '--silent')),
	verbose = Argument(0, 'More info at response', ('-v', '--verbose')),
	version = VersionArgument(0, 'Print current version', ('-V', '--version')),
	options = CmdLineConfigArgument(_config_arg, 'Override a config value', ('-o', '--options'))
)

def command():
	"""Class decorator that registers a class as a CLI command"""

	def decorator(cls):
		"""Any class with name of the form cmd1_cmd2_cmd3_... is accepted"""
		cls.description, sep, cls.long_description = cls.__doc__.partition('\n')

		# Generate a syntax string based on main's arguments
		spec = getargspec(cls.main.im_func)
		args = spec.args[1:]
		n = len(args) - len(spec.defaults or ())
		required = ' '.join('<%s>' % x.replace('____', '[:').replace('___', ':').replace('__',']').\
			replace('_', ' ') for x in args[:n])
		optional = ' '.join('[%s]' % x.replace('____', '[:').replace('___', ':').replace('__', ']').\
			replace('_', ' ') for x in args[n:])
		cls.syntax = ' '.join(x for x in [required, optional] if x)
		if spec.varargs:
			cls.syntax += ' <%s ...>' % spec.varargs

		_commands.add(cls.__name__, cls)
		return cls
	return decorator

def _init_parser(exe):
	parser = ArgumentParser(add_help=True)
	parser.prog='%s <cmd_group> [<cmd_subbroup> ...] <cmd>'%exe
	for name, argument in _arguments.items():
		argument.update_parser(parser, name)
	return parser

def parse_known_args(parser):
	parsed, unparsed = parser.parse_known_args()
	for name, arg in _arguments.items():
		arg.value = getattr(parsed, name, arg.value)
	return parsed, unparsed

def one_command():
	exe = basename(argv[0])
	parser = _init_parser(exe)
	parsed, unparsed = parse_known_args(parser)


def run_one_command():
	try:
		one_command()
	except CLIError as err:
		errmsg = '%s'%unicode(err) +' (%s)'%err.status if err.status else ' '
		font_color = yellow if err.importance <= 1 else magenta if err.importance <=2 else red
		from sys import stdout
		stdout.write(font_color(errmsg))
		if err.details is not None and len(err.details) > 0:
			print(': %s'%err.details)
		else:
			print
		exit(1)

