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

from re import compile as regex_compile
from .errors import CLIError

try:
    from colors import magenta, red, yellow, bold
except ImportError:
    # No colours? No worries, use dummy foo instead
    def dummy(val):
        return val
    red = yellow = magenta = bold = dummy


def remove_colors():
    global bold
    global red
    global yellow
    global magenta

    def dummy(val):
        return val
    red = yellow = magenta = bold = dummy


def pretty_keys(d, delim='_', recurcive=False):
    """<term>delim<term> to <term> <term> transformation
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


def print_dict(d, exclude=(), ident=0):
    if not isinstance(d, dict):
        raise CLIError(message='Cannot dict_print a non-dict object')

    if d:
        margin = max(len(unicode(key).strip())\
            for key in d.keys() if key not in exclude)

    for key, val in sorted(d.items()):
        if key in exclude:
            continue
        print_str = ' ' * ident
        print_str += ('%s' % key).strip()
        print_str += ' ' * (margin - len(unicode(key).strip()))
        print_str += ': '
        if isinstance(val, dict):
            print(print_str)
            print_dict(val, exclude=exclude, ident=margin + ident)
        elif isinstance(val, list):
            print(print_str)
            print_list(val, exclude=exclude, ident=margin + ident)
        else:
            print print_str + ' ' + unicode(val).strip()


def print_list(l, exclude=(), ident=0):
    if not isinstance(l, list):
        raise CLIError(message='Cannot list_print a non-list object')

    if l:
        margin = max(len(unicode(item).strip())\
            for item in l if item not in exclude)

    for item in sorted(l):
        if item in exclude:
            continue
        if isinstance(item, dict):
            print_dict(item, exclude=exclude, ident=margin + ident)
        elif isinstance(item, list):
            print_list(item, exclude=exclude, ident=margin + ident)
        else:
            print ' ' * ident + unicode(item)


def print_items(items, title=('id', 'name')):
    for item in items:
        if isinstance(item, dict) or isinstance(item, list):
            header = ' '.join(unicode(item.pop(key))\
                for key in title if key in item)
            print(' ')
            print(bold(header))
        if isinstance(item, dict):
            print_dict(item, ident=2)
        elif isinstance(item, list):
            print_list(item, ident=2)


def format_size(size):
    units = ('B', 'K', 'M', 'G', 'T')
    try:
        size = float(size)
    except ValueError:
        raise CLIError(message='Cannot format %s in bytes' % size)
    for unit in units:
        if size < 1024:
            break
        size /= 1024
    s = ('%.1f' % size)
    if '.0' == s[-2:]:
        s = s[:-2]
    return s + unit


def dict2file(d, f, depth=0):
    for k, v in d.items():
        f.write('%s%s: ' % ('\t' * depth, k))
        if isinstance(v, dict):
            f.write('\n')
            dict2file(v, f, depth + 1)
        elif isinstance(v, list):
            f.write('\n')
            list2file(v, f, depth + 1)
        else:
            f.write(' %s\n' % unicode(v))


def list2file(l, f, depth=1):
    for item in l:
        if isinstance(item, dict):
            dict2file(item, f, depth + 1)
        elif isinstance(item, list):
            list2file(item, f, depth + 1)
        else:
            f.write('%s%s\n' % ('\t' * depth, unicode(item)))

# Split input auxiliary


def _parse_with_regex(line, regex):
    re_parser = regex_compile(regex)
    return (re_parser.split(line), re_parser.findall(line))


def _sub_split(line):
    terms = []
    (sub_trivials, sub_interesting) = _parse_with_regex(line, ' ".*?" ')
    for subi, subipart in enumerate(sub_interesting):
        terms += sub_trivials[subi].split()
        terms.append(subipart[2:-2])
    terms += sub_trivials[-1].split()
    return terms


def split_input(line):
    """Use regular expressions to split a line correctly
    """
    line = ' %s ' % line
    (trivial_parts, interesting_parts) = _parse_with_regex(line, ' \'.*?\' ')
    terms = []
    for i, ipart in enumerate(interesting_parts):
        terms += _sub_split(trivial_parts[i])
        terms.append(ipart[2:-2])
    terms += _sub_split(trivial_parts[-1])
    return terms
