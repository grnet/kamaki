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

from .errors import CLIUnknownCommand, CLICmdIncompleteError, CLICmdSpecError, CLIError

class CommandTree(object):
    """A tree of command terms usefull for fast commands checking
    """

    def __init__(self, run_class=None, description='', commands={}):
        self.run_class = run_class
        self.description = description
        self.commands = commands
                
    def get_command_names(self, prefix=[]):
        cmd = self.get_command(prefix)
        return cmd.commands.keys()

    def get_terminal_commands(self, prefix=''):
        cmd = self.get_command(prefix)
        terminal_cmds = [prefix] if cmd.is_command() else []
        prefix = '' if len(prefix) == 0 else '%s_'%prefix
        for term, tree in cmd.commands.items():
            xtra = self.get_terminal_commands(prefix+term)
            terminal_cmds.append(*xtra)
        return terminal_cmds

    def add_path(self, command, description):
        path = get_pathlist_from_prefix(command)
        tmp = self
        for term in path:
            try:
                tmp = tmp.get_command(term)
            except CLIUnknownCommand:
                tmp.add_command(term)
                tmp = tmp.get_command(term)
        tmp.description = description

    def add_command(self, new_command, new_descr='', new_class=None):
        cmd_list = new_command.split('_')
        cmd = self.get_command(cmd_list[:-1])
        try:
            existing = cmd.get_command(cmd_list[-1])
            if new_class is not None:
                existing.run_class = new_class
            if new_descr not in (None, ''):
                existing.description = new_descr
        except CLIUnknownCommand:
            cmd.commands[new_command] = CommandTree(new_class,new_descr,{})

    def is_command(self, command=''):
        if self.get_command(command).run_class is None:
            return False
        return True

    def get_class(self, command=''):
        cmd = self.get_command(command)
        return cmd.run_class
    def set_class(self, command, new_class):
        cmd = self.get_command(command)
        cmd.run_class = new_class

    def get_description(self, command):
        cmd = self.get_command(command)
        return cmd.description
    def set_description(self, command, new_descr):
        cmd = self.get_command(command)
        cmd.description = new_descr

    def closest_complete_command(self, command):
        path = get_pathlist_from_prefix(command)
        tmp = self
        choice = self
        for term in path:
            tmp = tmp.get_command(term)
            if tmp.is_command():
                choice = tmp
        return choice

    def closest_description(self, command):
        path = get_pathlist_from_prefix(command)
        desc = self.description
        tmp = self
        for term in path:
            tmp = tmp.get_command(term)
            if tmp.description not in [None, '']:
                desc = tmp.description
        return desc

    def copy_command(self, prefix=''):
        cmd = self.get_command(prefix)
        from copy import deepcopy
        return deepcopy(cmd)

    def get_command(self, command):
        """
        @return a tuple of the form (cls_object, 'description text', {term1':(...), 'term2':(...)})
        """
        path = get_pathlist_from_prefix(command)
        cmd = self
        try:
            for term in path:
                cmd = cmd.commands[term]
        except KeyError:
            error_index = path.index(term)
            details='Command term %s not in path %s'%(unicode(term), path[:error_index])
            raise CLIUnknownCommand('Unknown command', details=details)
        return cmd

    def print_tree(self, command=[], level = 0, tabs=0):
        cmd = self.get_command(command)
        command_str = '_'.join(command) if isinstance(command, list) else command
        print('   '*tabs+command_str+': '+cmd.description)
        if level != 0:
            for name in cmd.get_command_names():
                new_level = level if level < 0 else (level-1)
                cmd.print_tree(name, new_level, tabs+1)

def get_pathlist_from_prefix(prefix):
    if isinstance(prefix, list):
        return prefix
    if len(prefix) == 0:
        return []
    return unicode(prefix).split('_')

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