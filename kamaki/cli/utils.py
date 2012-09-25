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
try:
    from colors import magenta, red, yellow, bold
except ImportError:
    #No colours? No worries, use dummy foo instead
    def bold(val):
        return val
    red = yellow = magenta = bold

from .errors import CLIUnknownCommand, CLICmdSpecError, CLIError

"""
def magenta(val):
    return magenta(val)
def red(val):
    return red(val)
def yellow(val):
    return yellow(val)
def bold(val):
    return bold(val)
"""

class CommandTree(object):
    """A tree of command terms usefull for fast commands checking
    None key is used to denote that its parent is a terminal symbol
    and also the command spec class
    e.g. add(store_list_all) will result to this:
        {'store': {
            'list': {
                'all': {
                    '_class':<store_list_all class>
                }
            }
        }
    then add(store_list) and store_info will create this:
        {'store': {
            'list': {
                '_class': <store_list class>
                'all': {
                    '_description': 'detail list of all containers in account'
                    '_class': <store_list_all class>
                },
            'info': {
                '_class': <store_info class>
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

    def __init__(self):
        self._commands = {}

    def _get_commands_from_prefix(self, prefix):
        path = get_pathlist_from_prefix(prefix)
        next_list = self._commands
        try:
            for cmd in path:
                next_list = next_list[unicode(cmd)]
        except TypeError, KeyError:
            error_index = path.index(cmd)
            details='Command %s not in path %s'%(unicode(cmd), path[:error_index])
            raise CLIUnknownCommand('Unknown command', details=details)
        assert isinstance(next_list,dict)
        return next_list 

    def list(self, prefix=[]):
        """ List the commands after prefix
        @param prefix can be either cmd1_cmd2_... or ['cmd1', 'cmd2', ...]
        """
        next_list =  self._get_commands_from_prefix(prefix)
        ret = next_list.keys()
        try:
            ret = ret.remove('_description')
        except ValueError:
            pass
        try:
            return ret.remove('_class')
        except ValueError:
            return ret

    def is_full_command(self, command):
        """ Check if a command exists as a full/terminal command
        e.g. store_list is full, store is partial, stort is not existing
        @param command can either be a cmd1_cmd2_... str or a ['cmd1, cmd2, ...'] list
        @return True if this command is in this Command Tree, False otherwise
        @raise CLIUnknownCommand if command is unknown to this tree
        """
        next_level = self._get_commands_from_prefix(command)
        if '_class' in next_level.keys():
            return True
        return False

    def add(self, command, cmd_class):
        """Add a command_path-->cmd_class relation to the path """
        path_list = get_pathlist_from_prefix(command)
        cmds = self._commands
        for cmd in path_list:
            if not cmds.has_key(cmd):
                cmds[cmd] = {}
            cmds = cmds[cmd]
        cmds['_class'] = cmd_class #make it terminal

    def set_description(self, command, description):
        """Add a command_path-->description to the path"""
        path_list = get_pathlist_from_prefix(command)
        cmds = self._commands
        for cmd in path_list:
            try:
                cmds = cmds[cmd]
            except KeyError:
                raise CLIUnknownCommand('set_description to cmd %s failed: cmd not found'%command)
        cmds['_description'] = description
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
            raise CLICmdSpecError('Cmd Spec Package %s load failed'%spec_package)

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
        if not loaded:
            raise CLICmdSpecError('Cmd Spec %s load failed'%spec)

def get_pathlist_from_prefix(prefix):
    return prefix if isinstance(prefix,list) else unicode(prefix).split('_')

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
        if isinstance(v,dict):
            f.write('\n')
            dict2file(v, f, depth+1)
        elif isinstance(v,list):
            f.write('\n')
            list2file(v, f, depth+1)
        else:
            f.write(' %s\n'%unicode(v))

def list2file(l, f, depth = 1):
    for item in l:
        if isinstance(item,dict):
            dict2file(item, f, depth+1)
        elif isinstance(item,list):
            list2file(item, f, depth+1)
        else:
            f.write('%s%s\n'%('\t'*depth, unicode(item)))