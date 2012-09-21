#A. One-command CLI
#	1. Get a command string
#	2. Parse out some Arguments
#		a. We need an Argument "library" for each command-level
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
#	5. Parse out some more Arguemnts 
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