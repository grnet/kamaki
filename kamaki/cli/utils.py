# Copyright 2011 GRNET S.A. All rights reserved.
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
from .errors import CLIUnknownCommand, CLISyntaxError, CLICmdSpecError

class Argument(Object):
    """An argument that can be parsed from command line or otherwise"""

    def __init__(self, name, arity, help=None, parsed_name=None):
        self.name = name
        self.arity = int(arity)

        if help is not None:
            self.help = help
        if parsed_name is not None:
            self.parsed_name = parsed_name

    @property 
    def name(self):
        return getattr(self, '_name', None)
    @name.setter
    def name(self, newname):
        self._name = unicode(newname)

    @property 
    def parsed_name(self):
        return getattr(self, '_parsed_name', None)
    @parsed_name.setter
    def parsed_name(self, newname):
        self._parsed_name = getattr(self, '_parsed_name', [])
        if isinstance(newname, list):
            self._parsed_name += newname
        else:
            self._parsed_name.append(unicode(newname))

    @property 
    def help(self):
        return getattr(self, '_help', None)
    @help.setter
    def help(self, newhelp):
        self._help = unicode(newhelp)

    @property 
    def arity(self):
        return getattr(self, '_arity', None)
    @arity.setter
    def arity(self, newarity):
        newarity = int(newarity)
        assert newarity >= 0
        self._arity = newarity

    @property 
    def default(self):
        if not hasattr(self, '_default'):
            self._default = False if self.arity == 0 else None
        return self._default
    @default.setter
    def default(self, newdefault):
        self._default = newdefault

    @property 
    def value(self):
        return getattr(self, '_value', self.default)
    @value.setter
    def value(self, newvalue):
        self._value = newvalue

    def update_parser(self, parser):
        """Update an argument parser with this argument info"""
        action = 'store_true' if self.arity == 0 else 'store'
        parser.add_argument(*(self.parsed_name), dest=self.name, action=action,
            default=self.default, help=self.help)

    @classmethod
    def test(self):
        h = Argument('heelp', 0, help='Display a help massage', parsed_name=['--help', '-h'])
        b = Argument('bbb', 1, help='This is a bbb', parsed_name='--bbb')
        c = Argument('ccc', 3, help='This is a ccc', parsed_name='--ccc')

        from argparse import ArgumentParser
        parser = ArgumentParser(add_help=False)
        h.update_parser(parser)
        b.update_parser(parser)
        c.update_parser(parser)

        args, argv = parser.parse_known_args()
        print('args: %s\nargv: %s'%(args, argv))

class CommandTree(Object):
    """A tree of command terms usefull for fast commands checking
    None key is used to denote that its parent is a terminal symbol
    and also the command spec class
    e.g. add(store_list_all) will result to this:
        {'store': {
            'list': {
                'all': {
                    '_spec':<store_list_all class>
                }
            }
        }
    then add(store_list) and store_info will create this:
        {'store': {
            'list': {
                None: <store_list class>
                'all': {
                    None: <store_list_all class>
                },
            'info': {
                None: <store_info class>
                }
            }
        }
    """

    cmd_spec_locations = [
        'kamaki.cli.commands',
        'kamaki.commands',
        'kamaki.cli',
        'kamaki',
        '']

    def __init__(self, zero_level_commands = []):
        self._commands = {}
        for cmd in zero_level_commands:
            self._commands[unicode(cmd)] = None

    def _get_commands_from_prefix(self, prefix):
        next_list = get_pathlist_from_prefix(prefix)
        try:
            for cmd in prefix:
                next_list = next_list[unicode(cmd)]
        except TypeError, KeyError:
            error_index = prefix.index(cmd)
            raise CLIUnknownCommand(message='Unknown command',
                details='Command %s not in path %s'%(unicode(cmd), unicode(prefix[:error_index)))
        assert next_list is dict
        return next_list 

    def list(prefix=[]):
        """ List the commands after prefix
        @param prefix can be either cmd1_cmd2_... or ['cmd1', 'cmd2', ...]
        """
        next_list =  self._get_commands_from_prefix(prefix)
        try:
            return next_list.keys().remove(None)
        except ValueError:
            return next_list.keys()

    def is_full_command(self, command):
        """ Check if a command exists as a full/terminal command
        e.g. store_list is full, store is partial, stort is not existing
        @param command can either be a cmd1_cmd2_... str or a ['cmd1, cmd2, ...'] list
        @return True if this command is in this Command Tree, False otherwise
        @raise CLIUnknownCommand if command is unknown to this tree
        """
        next_level = self._get_commands_from_prefix(command)
        if None in next_level.keys():
            return True
        return False

    def add(command, cmd_class):
        path_list = get_pathlist_from_prefix(command)
        d = self._commands
        for cmd in path_list:
            if not d.has_key(cmd):
                d[cmd] = {}
            d = d[cmd]
        d[None] = cmd_class #make it terminal

    def load_spec_package(self, spec_package):
        loaded = False
        for location in self.cmd_spec_locations:
            location += spec_package if location == '' else '.%s'%spec_package
            try:
                __import__(location) #a class decorator will put evetyrhing in place
                loaded = True
                break
            except ImportError:
                pass
        if not loaded:
            raise CLICmdSpecError(message='Cmd Spec Package %s load failed'%spec_package)

    def load_spec(self, spec_package, spec):
        """Load spec from a non nessecery loaded spec package"""

        loaded = False
        for location in self.cmd_spec_locations:
            location += spec_package if location == '' else '.%s'%spec_package
            try:
                __import__(location, fromlist=[spec])
                loaded = True
                break
            except ImportError:
                pass
        if not loaded
            raise CLICmdSpecError(message='Cmd Spec %s load failed'%spec)


def get_pathlist_from_prefix(prefix):
    return prefix if prefix is list else unicode(prefix).split('_')

def pretty_keys(d, delim='_', recurcive=False):
    """Transform keys of a dict from the form
    str1_str2_..._strN to the form strN
    where _ is the delimeter
    """
    new_d = {}
    for key, val in d.items():
        new_key = key.split(delim)[-1]
        if recurcive and isinstance(val, dict):
            new_val = pretty_keys(val, delim, recurcive) 
        else:
            new_val = val
        new_d[new_key] = new_val
    return new_d

def print_dict(d, exclude=(), ident= 0):
    if not isinstance(d, dict):
        raise CLIError(message='Cannot dict_print a non-dict object')
    try:
        margin = max(
            1 + max(len(unicode(key).strip()) for key in d.keys() \
                if not isinstance(key, dict) and not isinstance(key, list)),
            ident)
    except ValueError:
        margin = ident

    for key, val in sorted(d.items()):
        if key in exclude:
            continue
        print_str = '%s:' % unicode(key).strip()
        if isinstance(val, dict):
            print(print_str.rjust(margin)+' {')
            print_dict(val, exclude = exclude, ident = margin + 6)
            print '}'.rjust(margin)
        elif isinstance(val, list):
            print(print_str.rjust(margin)+' [')
            print_list(val, exclude = exclude, ident = margin + 6)
            print ']'.rjust(margin)
        else:
            print print_str.rjust(margin)+' '+unicode(val).strip()

def print_list(l, exclude=(), ident = 0):
    if not isinstance(l, list):
        raise CLIError(message='Cannot list_print a non-list object')
    try:
        margin = max(
            1 + max(len(unicode(item).strip()) for item in l \
                if not isinstance(item, dict) and not isinstance(item, list)),
            ident)
    except ValueError:
        margin = ident

    for item in sorted(l):
        if item in exclude:
            continue
        if isinstance(item, dict):
            print('{'.rjust(margin))
            print_dict(item, exclude = exclude, ident = margin + 6)
            print '}'.rjust(margin)
        elif isinstance(item, list):
            print '['.rjust(margin)
            print_list(item, exclude = exclude, ident = margin + 6)
            print ']'.rjust(margin)
        else:
            print unicode(item).rjust(margin)

def print_items(items, title=('id', 'name')):
    for item in items:
        if isinstance(item, dict) or isinstance(item, list):
            print ' '.join(unicode(item.pop(key)) for key in title if key in item)
        if isinstance(item, dict):
            print_dict(item)

def format_size(size):
    units = ('B', 'K', 'M', 'G', 'T')
    try:
        size = float(size)
    except ValueError:
        raise CLIError(message='Cannot format %s in bytes'%size)
    for unit in units:
        if size < 1024:
            break
        size /= 1024
    s = ('%.1f' % size)
    if '.0' == s[-2:]:
        s = s[:-2]
    return s + unit

def dict2file(d, f, depth = 0):
    for k, v in d.items():
        f.write('%s%s: '%('\t'*depth, k))
        if type(v) is dict:
            f.write('\n')
            dict2file(v, f, depth+1)
        elif type(v) is list:
            f.write('\n')
            list2file(v, f, depth+1)
        else:
            f.write(' %s\n'%unicode(v))

def list2file(l, f, depth = 1):
    for item in l:
        if type(item) is dict:
            dict2file(item, f, depth+1)
        elif type(item) is list:
            list2file(item, f, depth+1)
        else:
            f.write('%s%s\n'%('\t'*depth, unicode(item)))