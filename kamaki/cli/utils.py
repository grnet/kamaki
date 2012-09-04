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
from . import CLIError
from colors import underline

def raiseCLIError(err, importance = -1):
    if importance < 0:
        if err.status <= 0:
            importance = 0
        elif err.status <= 400:
            importance = 1
        elif err.status <= 500:
            importance = 2
        else:
            importance = 3
    raise CLIError(err.message, err.status, err.details, importance)

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