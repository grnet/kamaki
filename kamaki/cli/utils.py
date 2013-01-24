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

from sys import stdout, stdin
from re import compile as regex_compile
from kamaki.cli.errors import raiseCLIError

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


def print_dict(d,
    exclude=(),
    ident=0,
    with_enumeration=False,
    recursive_enumeration=False):
    """
    Pretty-print a dictionary object

    :param d: (dict) the input

    :param excelude: (set or list) keys to exclude from printing

    :param ident: (int) initial indentation (recursive)

    :param with_enumeration: (bool) enumerate each 1st level key if true

    :recursive_enumeration: (bool) recursively enumerate dicts and lists of
        2nd level or deeper

    :raises CLIError: (TypeError wrapper) non-dict input
    """
    if not isinstance(d, dict):
        raiseCLIError(TypeError('Cannot dict_print a non-dict object'))

    if d:
        margin = max(len(unicode(key).strip())\
            for key in d.keys() if key not in exclude)

    counter = 1
    for key, val in sorted(d.items()):
        if key in exclude:
            continue
        print_str = ''
        if with_enumeration:
            print_str = '%s. ' % counter
            counter += 1
        print_str = '%s%s' % (' ' * (ident - len(print_str)), print_str)
        print_str += ('%s' % key).strip()
        print_str += ' ' * (margin - len(unicode(key).strip()))
        print_str += ': '
        if isinstance(val, dict):
            print(print_str)
            print_dict(val,
                exclude=exclude,
                ident=margin + ident,
                with_enumeration=recursive_enumeration,
                recursive_enumeration=recursive_enumeration)
        elif isinstance(val, list):
            print(print_str)
            print_list(val,
                exclude=exclude,
                ident=margin + ident,
                with_enumeration=recursive_enumeration,
                recursive_enumeration=recursive_enumeration)
        else:
            print print_str + ' ' + unicode(val).strip()


def print_list(l,
    exclude=(),
    ident=0,
    with_enumeration=False,
    recursive_enumeration=False):
    """
    Pretty-print a list object

    :param l: (list) the input

    :param excelude: (object - anytype) values to exclude from printing

    :param ident: (int) initial indentation (recursive)

    :param with_enumeration: (bool) enumerate each 1st level value if true

    :recursive_enumeration: (bool) recursively enumerate dicts and lists of
        2nd level or deeper

    :raises CLIError: (TypeError wrapper) non-list input
    """
    if not isinstance(l, list):
        raiseCLIError(TypeError('Cannot list_print a non-list object'))

    if l:
        try:
            margin = max(len(unicode(item).strip()) for item in l\
                if not (isinstance(item, dict)\
                or isinstance(item, list)\
                or item in exclude))
        except ValueError:
            margin = (2 + len(unicode(len(l)))) if enumerate else 1

    counter = 1
    prefix = ''
    for item in sorted(l):
        if item in exclude:
            continue
        elif with_enumeration:
            prefix = '%s. ' % counter
            counter += 1
            prefix = '%s%s' % (' ' * (ident - len(prefix)), prefix)
        else:
            prefix = ' ' * ident
        if isinstance(item, dict):
            if with_enumeration:
                print(prefix)
            print_dict(item,
                exclude=exclude,
                ident=margin + ident,
                with_enumeration=recursive_enumeration,
                recursive_enumeration=recursive_enumeration)
        elif isinstance(item, list):
            if with_enumeration:
                print(prefix)
            print_list(item,
                exclude=exclude,
                ident=margin + ident,
                with_enumeration=recursive_enumeration,
                recursive_enumeration=recursive_enumeration)
        else:
            print('%s%s' % (prefix, item))


def page_hold(index, limit, maxlen):
    """Check if there are results to show, and hold the page when needed
    :param index: (int) > 0
    :param limit: (int) 0 < limit <= max, page hold if limit mod index == 0
    :param maxlen: (int) Don't hold if index reaches maxlen

    :returns: True if there are more to show, False if all results are shown
    """
    if index >= limit and index % limit == 0:
        if index >= maxlen:
            return False
        else:
            print('(%s listed - %s more - "enter" to continue)' % (
                index,
                maxlen - index))
            c = ' '
            while c != '\n':
                c = stdin.read(1)
    return True


def print_items(items,
    title=('id', 'name'),
    with_enumeration=False,
    with_redundancy=False,
    page_size=0):
    """print dict or list items in a list, using some values as title
    Objects of next level don't inherit enumeration (default: off) or titles

    :param items: (list) items are lists or dict
    :param title: (tuple) keys to use their values as title
    :param with_enumeration: (boolean) enumerate items (order id on title)
    :param with_redundancy: (boolean) values in title also appear on body
    :param page_size: (int) show results in pages of page_size items, enter to
        continue
    """
    if not items:
        return
    try:
        page_size = int(page_size) if int(page_size) > 0 else len(items)
    except:
        page_size = len(items)
    num_of_pages = len(items) // page_size
    num_of_pages += 1 if len(items) % page_size else 0
    for i, item in enumerate(items):
        if with_enumeration:
            stdout.write('%s. ' % (i + 1))
        if isinstance(item, dict):
            title = sorted(set(title).intersection(item.keys()))
            if with_redundancy:
                header = ' '.join(unicode(item[key]) for key in title)
            else:
                header = ' '.join(unicode(item.pop(key)) for key in title)
            print(bold(header))
        else:
            print('- - -')
        if isinstance(item, dict):
            print_dict(item, ident=1)
        elif isinstance(item, list):
            print_list(item, ident=1)
        else:
            print(' %s' % item)
        page_hold(i + 1, page_size, len(items))


def format_size(size):
    units = ('B', 'K', 'M', 'G', 'T')
    try:
        size = float(size)
    except ValueError as err:
        raiseCLIError(err, 'Cannot format %s in bytes' % size)
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
