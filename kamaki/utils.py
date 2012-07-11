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

def print_dict(d, exclude=(), ident= 0):
    if 0 == len(d):
        return
    margin = max(1 + max(len(unicode(key)) for key in d), ident)
    for key, val in d.items():
        if key in exclude:
            continue
        print_str = '%s:' % unicode(key)
        if isinstance(val, dict):
            print(print_str.rjust(margin)+' {')
            print_dict(val, exclude = exclude, ident = margin + 6)
            print '}'.rjust(margin)
        elif isinstance(val, list):
            print(print_str.rjust(margin)+' [')
            print_list(val, exclude = exclude, ident = margin + 6)
            print ']'.rjust(margin)
        else:
            print print_str.rjust(margin)+' '+unicode(val)

def print_list(l, exclude=(), ident = 0):
    if 0 == len(l):
        return
    margin = max(1 + max(len(unicode(item)) for item in l), ident)
    for item in l:
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
        print ' '.join(unicode(item.pop(key)) for key in title if key in item)
        if item:
            print_dict(item)
            print

def format_size(size):
    units = ('B', 'K', 'M', 'G', 'T')
    size = float(size)
    for unit in units:
        if size <= 1024:
            break
        size /= 1024
    s = ('%.1f' % size).rstrip('.0')
    return s + unit

