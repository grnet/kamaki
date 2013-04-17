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
from time import sleep
from os import walk, path

from kamaki.cli.errors import raiseCLIError

suggest = dict(
    ansicolors=dict(
        active=False,
        url='#install-ansicolors-progress',
        description='Add colors to console responses'),
    progress=dict(
        active=False,
        url='#install-ansicolors-progress',
        description='Add progress bars to some commands'))

try:
    from colors import magenta, red, yellow, bold
except ImportError:
    # No colours? No worries, use dummy foo instead
    def dummy(val):
        return val
    red = yellow = magenta = bold = dummy
    suggest['ansicolors']['active'] = True

try:
    from progress.bar import ShadyBar
except ImportError:
    suggest['progress']['active'] = True


def suggest_missing(miss=None):
    global suggest
    kamaki_docs = 'http://www.synnefo.org/docs/kamaki/latest'
    for k, v in (miss, suggest[miss]) if miss else suggest.items():
        if v['active'] and stdout.isatty():
            print('Suggestion: for better user experience install %s' % k)
            print('\t%s' % v['description'])
            print('\tIt is easy, here are the instructions:')
            print('\t%s/installation.html%s' % (kamaki_docs, v['url']))
            print('')


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


def print_dict(
        d, exclude=(), ident=0,
        with_enumeration=False, recursive_enumeration=False):
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
        margin = max(len(('%s' % key).strip()) for key in d.keys() if (
            key not in exclude))

    counter = 1
    for key, val in sorted(d.items()):
        key = '%s' % key
        if key in exclude:
            continue
        print_str = ''
        if with_enumeration:
            print_str = '%s. ' % counter
            counter += 1
        print_str = '%s%s' % (' ' * (ident - len(print_str)), print_str)
        print_str += key.strip()
        print_str += ' ' * (margin - len(key.strip()))
        print_str += ': '
        if isinstance(val, dict):
            print(print_str)
            print_dict(
                val,
                exclude=exclude,
                ident=margin + ident,
                with_enumeration=recursive_enumeration,
                recursive_enumeration=recursive_enumeration)
        elif isinstance(val, list):
            print(print_str)
            print_list(
                val,
                exclude=exclude,
                ident=margin + ident,
                with_enumeration=recursive_enumeration,
                recursive_enumeration=recursive_enumeration)
        else:
            print print_str + ' ' + ('%s' % val).strip()


def print_list(
        l, exclude=(), ident=0,
        with_enumeration=False, recursive_enumeration=False):
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
            margin = max(len(('%s' % item).strip()) for item in l if not (
                isinstance(item, dict) or
                isinstance(item, list) or
                item in exclude))
        except ValueError:
            margin = (2 + len(('%s' % len(l)))) if enumerate else 1

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
            print_dict(
                item,
                exclude=exclude,
                ident=margin + ident,
                with_enumeration=recursive_enumeration,
                recursive_enumeration=recursive_enumeration)
        elif isinstance(item, list):
            if with_enumeration:
                print(prefix)
            print_list(
                item,
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


def print_items(
        items, title=('id', 'name'),
        with_enumeration=False, with_redundancy=False,
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
                header = ' '.join('%s' % item[key] for key in title)
            else:
                header = ' '.join('%s' % item.pop(key) for key in title)
            print(bold(header))
        if isinstance(item, dict):
            print_dict(item, ident=1)
        elif isinstance(item, list):
            print_list(item, ident=1)
        else:
            print(' %s' % item)
        page_hold(i + 1, page_size, len(items))


def format_size(size):
    units = ('B', 'KiB', 'MiB', 'GiB', 'TiB')
    try:
        size = float(size)
    except ValueError as err:
        raiseCLIError(err, 'Cannot format %s in bytes' % size)
    for unit in units:
        if size < 1024:
            break
        size /= 1024.0
    s = ('%.2f' % size)
    while '.' in s and s[-1] in ('0', '.'):
        s = s[:-1]
    return s + unit


def to_bytes(size, format):
    """
    :param size: (float) the size in the given format
    :param format: (case insensitive) KiB, KB, MiB, MB, GiB, GB, TiB, TB

    :returns: (int) the size in bytes
    """
    format = format.upper()
    if format == 'B':
        return int(size)
    size = float(size)
    units_dc = ('KB', 'MB', 'GB', 'TB')
    units_bi = ('KIB', 'MIB', 'GIB', 'TIB')

    factor = 1024 if format in units_bi else 1000 if format in units_dc else 0
    if not factor:
        raise ValueError('Invalid data size format %s' % format)
    for prefix in ('K', 'M', 'G', 'T'):
        size *= factor
        if format.startswith(prefix):
            break
    return int(size)


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
            f.write(' %s\n' % v)


def list2file(l, f, depth=1):
    for item in l:
        if isinstance(item, dict):
            dict2file(item, f, depth + 1)
        elif isinstance(item, list):
            list2file(item, f, depth + 1)
        else:
            f.write('%s%s\n' % ('\t' * depth, item))

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


def old_split_input(line):
    """Use regular expressions to split a line correctly"""
    line = ' %s ' % line
    (trivial_parts, interesting_parts) = _parse_with_regex(line, ' \'.*?\' ')
    terms = []
    for i, ipart in enumerate(interesting_parts):
        terms += _sub_split(trivial_parts[i])
        terms.append(ipart[2:-2])
    terms += _sub_split(trivial_parts[-1])
    return terms


def _get_from_parsed(parsed_str):
    try:
        parsed_str = parsed_str.strip()
    except:
        return None
    if parsed_str:
        if parsed_str[0] == parsed_str[-1] and parsed_str[0] in ("'", '"'):
            return [parsed_str[1:-1]]
        return parsed_str.split(' ')
    return None


def split_input(line):
    if not line:
        return []
    reg_expr = '\'.*?\'|".*?"|^[\S]*$'
    (trivial_parts, interesting_parts) = _parse_with_regex(line, reg_expr)
    assert(len(trivial_parts) == 1 + len(interesting_parts))
    #print('  [split_input] trivial_parts %s are' % trivial_parts)
    #print('  [split_input] interesting_parts %s are' % interesting_parts)
    terms = []
    for i, tpart in enumerate(trivial_parts):
        part = _get_from_parsed(tpart)
        if part:
            terms += part
        try:
            part = _get_from_parsed(interesting_parts[i])
        except IndexError:
            break
        if part:
            terms += part
    return terms


def ask_user(msg, true_resp=['Y', 'y']):
    """Print msg and read user response

    :param true_resp: (tuple of chars)

    :returns: (bool) True if reponse in true responses, False otherwise
    """
    stdout.write('%s (%s or enter for yes):' % (msg, ', '.join(true_resp)))
    stdout.flush()
    user_response = stdin.readline()
    return user_response[0] in true_resp + ['\n']


def spiner(size=None):
    spins = ('/', '-', '\\', '|')
    stdout.write(' ')
    size = size or -1
    i = 0
    while size - i:
        stdout.write('\b%s' % spins[i % len(spins)])
        stdout.flush()
        i += 1
        sleep(0.1)
        yield
    yield

if __name__ == '__main__':
    examples = [
        'la_la le_le li_li',
        '\'la la\' \'le le\' \'li li\'',
        '\'la la\' le_le \'li li\'',
        'la_la \'le le\' li_li',
        'la_la \'le le\' \'li li\'',
        '"la la" "le le" "li li"',
        '"la la" le_le "li li"',
        'la_la "le le" li_li',
        '"la_la" "le le" "li li"',
        '\'la la\' "le le" \'li li\'',
        'la_la \'le le\' "li li"',
        'la_la \'le le\' li_li',
        '\'la la\' le_le "li li"',
        '"la la" le_le \'li li\'',
        '"la la" \'le le\' li_li',
        'la_la \'le\'le\' "li\'li"',
        '"la \'le le\' la"',
        '\'la "le le" la\'',
        '\'la "la" la\' "le \'le\' le" li_"li"_li',
        '\'\' \'L\' "" "A"']

    for i, example in enumerate(examples):
        print('%s. Split this: (%s)' % (i + 1, example))
        ret = old_split_input(example)
        print('\t(%s) of size %s' % (ret, len(ret)))


def get_path_size(testpath):
    if path.isfile(testpath):
        return path.getsize(testpath)
    total_size = 0
    for top, dirs, files in walk(path.abspath(testpath)):
        for f in files:
            f = path.join(top, f)
            if path.isfile(f):
                total_size += path.getsize(f)
    return total_size
