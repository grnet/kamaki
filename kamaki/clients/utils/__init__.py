# Copyright 2013-2014 GRNET S.A. All rights reserved.
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

import unicodedata


def _matches(val1, val2, exactMath=True):
    """Case Insensitive match"""

    return (val1.lower() == val2.lower()) if (
        exactMath) else val1.lower().startswith(val2.lower())


def filter_out(d, prefix, exactMatch=False):
    """Remove entries that are prefixed with prefix (case insensitive)

    :param d: (dict) input

    :param prefix: (str) prefix to match input keys against

    :param exactMatch: (bool) key should fully match if True, just prefixed
        with prefix if False

    :returns: (dict) the updated d
    """

    ret = dict()
    for key, val in d.items():
        if not _matches(key, prefix, exactMath=exactMatch):
            ret[key] = val
    return ret


def filter_in(d, prefix, exactMatch=False):
    """Keep only entries of d prefixed with prefix

    :param d: (dict) input

    :param prefix: (str) prefix to match input keys against

    :param exactMatch: (bool) key should fully match if True, just prefixed
        with prefix if False

    :returns: (dict) the updated d
    """
    ret = dict()
    for key, val in d.items():
        if _matches(key, prefix, exactMath=exactMatch):
            ret[key] = val
    return ret


def path4url(*args):
    """
    :param args: (list of str)

    :returns: (str) a path in the form /args[0]/args[1]/...
    """

    r = '/'.join([''] + [arg.decode('utf-8') if (
        isinstance(arg, str)) else '%s' % arg for arg in args])
    while '//' in r:
        r = r.replace('//', '/')
    return ('/%s' % r.strip('/')) if r else ''


def readall(openfile, size, retries=7):
    """Read a file until size is reached"""
    remains = size if size > 0 else 0
    buf = ''
    for i in range(retries):
        tmp_buf = openfile.read(remains)
        if tmp_buf:
            buf += tmp_buf
            remains -= len(tmp_buf)
            if remains > 0:
                continue
        return buf
    raise IOError('Failed to read %s bytes from file' % size)


def escape_ctrl_chars(s):
    """Escape control characters from unicode and string objects."""
    if isinstance(s, unicode):
        return "".join(ch.encode("unicode_escape") if (
            unicodedata.category(ch)[0]) == "C" else ch for ch in s)
    if isinstance(s, basestring):
        return "".join(
            [c if 31 < ord(c) < 127 else c.encode("string_escape") for c in s])
    return s
