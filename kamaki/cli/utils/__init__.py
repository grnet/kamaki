# Copyright 2011-2014 GRNET S.A. All rights reserved.
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

from sys import stdout, stderr
from re import compile as regex_compile
from os import walk, path
from json import dumps
from locale import getpreferredencoding

from kamaki.cli.logger import get_logger
from kamaki.cli.errors import raiseCLIError
from kamaki.clients.utils import escape_ctrl_chars

INDENT_TAB = 4
log = get_logger(__name__)
pref_enc = getpreferredencoding()


suggest = dict(ansicolors=dict(
    active=False,
    url='#install-ansicolors',
    description='Add colors to console responses'))

try:
    from colors import magenta, red, yellow, bold
except ImportError:
    red = yellow = magenta = bold = lambda x: x
    suggest['ansicolors']['active'] = True


def remove_colors():
    global bold
    global red
    global yellow
    global magenta
    red = yellow = magenta = bold = lambda x: x


def suggest_missing(miss=None, exclude=[]):
    global suggest
    sgs = dict(suggest)
    for exc in exclude:
        try:
            sgs.pop(exc)
        except KeyError:
            pass
    kamaki_docs = 'http://www.synnefo.org/docs/kamaki/latest'

    for k, v in (miss, sgs[miss]) if miss else sgs.items():
        if v['active'] and stderr.isatty():
            stderr.write('Suggestion: you may like to install %s\n' % k)
            stderr.write(
                ('%s\n' % v['description']).encode(pref_enc, 'replace'))
            stderr.write('\tIt is easy, here are the instructions:\n')
            stderr.write('\t%s/installation.html%s\n' % (
                kamaki_docs, v['url']))
            stderr.flush()


def guess_mime_type(
        filename,
        default_content_type='application/octet-stream',
        default_encoding=None):
    assert filename, 'Cannot guess mimetype for empty filename'
    try:
        from mimetypes import guess_type
        ctype, cenc = guess_type(filename)
        return ctype or default_content_type, cenc or default_encoding
    except ImportError:
        stderr.write('WARNING: Cannot import mimetypes, using defaults\n')
        stderr.flush()
        return (default_content_type, default_encoding)


def pretty_keys(d, delim='_', recursive=False):
    """<term>delim<term> to <term> <term> transformation"""
    new_d = dict(d)
    for k, v in d.items():
        new_v = new_d.pop(k)
        new_d[k.replace(delim, ' ').strip()] = pretty_keys(
            new_v, delim, True) if (
                recursive and isinstance(v, dict)) else new_v
    return new_d


def print_json(data, out=stdout):
    """Print a list or dict as json in console

    :param data: json-dumpable data

    :param out: Input/Output stream to dump values into
    """
    out.write(dumps(data, indent=INDENT_TAB))
    out.write(u'\n')


def print_dict(
        d,
        exclude=(), indent=0,
        with_enumeration=False, recursive_enumeration=False, out=stdout):
    """Pretty-print a dictionary object
    <indent>key: <non iterable item>
    <indent>key:
    <indent + INDENT_TAB><pretty-print iterable>

    :param d: (dict)

    :param exclude: (iterable of strings) keys to exclude from printing

    :param indent: (int) initial indentation (recursive)

    :param with_enumeration: (bool) enumerate 1st-level keys

    :param recursive_enumeration: (bool) recursively enumerate iterables (does
        not enumerate 1st level keys)

    :param out: Input/Output stream to dump values into

    :raises CLIError: if preconditions fail
    """
    assert isinstance(d, dict), 'print_dict input must be a dict'
    assert indent >= 0, 'print_dict indent must be >= 0'

    for i, (k, v) in enumerate(d.items()):
        k = ('%s' % k).strip()
        if k in exclude:
            continue
        print_str = ' ' * indent
        print_str += '%s.' % (i + 1) if with_enumeration else ''
        print_str += '%s:' % k
        if isinstance(v, dict):
            out.write(escape_ctrl_chars(print_str) + u'\n')
            print_dict(
                v, exclude, indent + INDENT_TAB,
                recursive_enumeration, recursive_enumeration, out)
        elif isinstance(v, list) or isinstance(v, tuple):
            out.write(escape_ctrl_chars(print_str) + u'\n')
            print_list(
                v, exclude, indent + INDENT_TAB,
                recursive_enumeration, recursive_enumeration, out)
        else:
            out.write(escape_ctrl_chars(u'%s %s' % (print_str, v)))
            out.write(u'\n')


def print_list(
        l,
        exclude=(), indent=0,
        with_enumeration=False, recursive_enumeration=False, out=stdout):
    """Pretty-print a list of items
    <indent>key: <non iterable item>
    <indent>key:
    <indent + INDENT_TAB><pretty-print iterable>

    :param l: (list)

    :param exclude: (iterable of strings) items to exclude from printing

    :param indent: (int) initial indentation (recursive)

    :param with_enumeration: (bool) enumerate 1st-level items

    :param recursive_enumeration: (bool) recursively enumerate iterables (does
        not enumerate 1st level keys)

    :param out: Input/Output stream to dump values into

    :raises CLIError: if preconditions fail
    """
    assert isinstance(l, list) or isinstance(l, tuple), (
        'print_list prinbts a list or tuple')
    assert indent >= 0, 'print_list indent must be >= 0'

    for i, item in enumerate(l):
        print_str = ' ' * indent
        print_str += '%s.' % (i + 1) if with_enumeration else ''
        if isinstance(item, dict):
            if with_enumeration:
                out.write(escape_ctrl_chars(print_str) + u'\n')
            elif i and i < len(l):
                out.write(u'\n')
            print_dict(
                item, exclude,
                indent + (INDENT_TAB if with_enumeration else 0),
                recursive_enumeration, recursive_enumeration, out)
        elif isinstance(item, list) or isinstance(item, tuple):
            if with_enumeration:
                out.write(escape_ctrl_chars(print_str) + u'\n')
            elif i and i < len(l):
                out.write(u'\n')
            print_list(
                item, exclude, indent + INDENT_TAB,
                recursive_enumeration, recursive_enumeration, out)
        else:
            item = ('%s' % item).strip()
            if item in exclude:
                continue
            out.write(escape_ctrl_chars(u'%s%s' % (print_str, item)))
            out.write(u'\n')


def print_items(
        items, title=('id', 'name'),
        with_enumeration=False, with_redundancy=False, out=stdout):
    """print dict or list items in a list, using some values as title
    Objects of next level don't inherit enumeration (default: off) or titles

    :param items: (list) items are lists or dict

    :param title: (tuple) keys to use their values as title

    :param with_enumeration: (boolean) enumerate items (order id on title)

    :param with_redundancy: (boolean) values in title also appear on body

    :param out: Input/Output stream to dump values into
    """
    if not items:
        return
    if not (isinstance(items, dict) or isinstance(items, list) or isinstance(
            items, tuple)):
        out.write(escape_ctrl_chars(u'%s' % items))
        out.write(u'\n')
        return

    for i, item in enumerate(items):
        if with_enumeration:
            out.write(u'%s. ' % (i + 1))
        if isinstance(item, dict):
            item = dict(item)
            title = sorted(set(title).intersection(item))
            pick = item.get if with_redundancy else item.pop
            header = escape_ctrl_chars(
                ' '.join('%s' % pick(key) for key in title))
            out.write((unicode(bold(header) if header else '') + '\n'))
            print_dict(item, indent=INDENT_TAB, out=out)
        elif isinstance(item, list) or isinstance(item, tuple):
            print_list(item, indent=INDENT_TAB, out=out)
        else:
            out.write(u' %s\n' % escape_ctrl_chars(item))


def format_size(size, decimal_factors=False):
    units = ('B', 'KB', 'MB', 'GB', 'TB') if decimal_factors else (
        'B', 'KiB', 'MiB', 'GiB', 'TiB')
    step = 1000 if decimal_factors else 1024
    fstep = float(step)
    try:
        size = float(size)
    except (ValueError, TypeError) as err:
        raiseCLIError(err, 'Cannot format %s in bytes' % (
            ','.join(size) if isinstance(size, tuple) else size))
    for i, unit in enumerate(units):
        if size < step or i + 1 == len(units):
            break
        size /= fstep
    s = ('%.2f' % size)
    s = s.replace('%s' % step, '%s.99' % (step - 1)) if size <= fstep else s
    while '.' in s and s[-1] in ('0', '.'):
        s = s[:-1]
    return s + unit


def to_bytes(size, format):
    """
    :param size: (float) the size in the given format
    :param format: (case insensitive) KiB, KB, MiB, MB, GiB, GB, TiB, TB

    :returns: (int) the size in bytes
    :raises ValueError: if invalid size or format
    :raises AttributeError: if format is not str
    :raises TypeError: if size is not arithmetic or convertible to arithmetic
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
        f.write('%s%s: ' % (' ' * INDENT_TAB * depth, k))
        if isinstance(v, dict):
            f.write('\n')
            dict2file(v, f, depth + 1)
        elif isinstance(v, list) or isinstance(v, tuple):
            f.write('\n')
            list2file(v, f, depth + 1)
        else:
            f.write('%s\n' % v)


def list2file(l, f, depth=1):
    for item in l:
        if isinstance(item, dict):
            dict2file(item, f, depth + 1)
        elif isinstance(item, list) or isinstance(item, tuple):
            list2file(item, f, depth + 1)
        else:
            f.write('%s%s\n' % (' ' * INDENT_TAB * depth, item))

# Split input auxiliary


def _get_from_parsed(parsed_str):
    try:
        parsed_str = parsed_str.strip()
    except:
        return None
    return ([parsed_str[1:-1]] if (
        parsed_str[0] == parsed_str[-1] and parsed_str[0] in ("'", '"')) else (
            parsed_str.split(' '))) if parsed_str else None


def split_input(line):
    terms = []
    if line:
        rprs = regex_compile('\'.*?\'|".*?"|^[\S]*$')
        trivial_parts, interesting_parts = rprs.split(line), rprs.findall(line)
        assert(len(trivial_parts) == 1 + len(interesting_parts))
        for i, tpart in enumerate(trivial_parts):
            part = _get_from_parsed(tpart)
            if part:
                terms += part
            try:
                part = _get_from_parsed(interesting_parts[i])
            except IndexError:
                break
            if part:
                if tpart and not tpart[-1].endswith(' '):
                    terms[-1] += ' '.join(part)
                else:
                    terms += part
    return terms


def ask_user(msg, true_resp=('y', ), **kwargs):
    """Print msg and read user response

    :param true_resp: (tuple of chars)

    :returns: (bool) True if reponse in true responses, False otherwise
    """
    yep = u', '.join(true_resp)
    nope = u'<not %s>' % yep if 'n' in true_resp or 'N' in true_resp else 'N'
    msg = escape_ctrl_chars(msg).encode(pref_enc, 'replace')
    yep = yep.encode(pref_enc, 'replace')
    nope = nope.encode(pref_enc, 'replace')
    response = raw_input(
        '%s [%s/%s]: ' % (msg, yep, nope))
    # Pressing just enter gives an empty response!
    user_response = response if response else 'N'
    return user_response[0].lower() in [s.lower() for s in true_resp]


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


def remove_from_items(list_of_dicts, key_to_remove):
    for item in list_of_dicts:
        assert isinstance(item, dict), 'Item %s not a dict' % item
        item.pop(key_to_remove, None)


def filter_dicts_by_dict(
        list_of_dicts, filters, exact_match=True, case_sensitive=False):
    """
    :param list_of_dicts: (list) each dict contains "raw" key-value pairs

    :param filters: (dict) filters in key-value form

    :param exact_match: (bool) if false, check if the filter value is part of
        the actual value

    :param case_sensitive: (bool) refers to values only (not keys)

    :returns: (list) only the dicts that match all filters
    """
    new_dicts = []
    for d in list_of_dicts:
        if set(filters).difference(d):
            continue
        match = True
        for k, v in filters.items():
            dv, v = ('%s' % d[k]), ('%s' % v)
            if not case_sensitive:
                dv, v = dv.lower(), v.lower()
            if not ((
                    exact_match and v == dv) or (
                    (not exact_match) and v in dv)):
                match = False
                break
        if match:
            new_dicts.append(d)
    return new_dicts
