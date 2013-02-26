# Copyright 2011-2012 GRNET S.A. All rights reserved.
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


def _matches(val1, val2, exactMath=True):
    """Case Insensitive match"""

    if exactMath:
        return True if val1.lower() == val2.lower() else False
    else:
        return True if val1.lower().startswith(val2.lower()) else False


def filter_out(d, prefix, exactMatch=False):
    """Remove entries that are prefixed with prefix (case insensitive)

    :param d: (dict) input

    :param prefix: (str) prefix to match input keys against

    :param exactMatch: (bool) key should fully match if True, just prefixed
        with prefix if False

    :returns: (dict) the updated d
    """

    ret = {}
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
    ret = {}
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


def params4url(params):
    """{'key1':'val1', 'key2':None, 'key3':15} --> "?key1=val1&key2&key3=15"

    :param params: (dict) request parameters in the form key:val

    :returns: (str) http-request friendly in the form ?key1=val1&key2=val2&...
    """

    assert(type(params) is dict)
    result = ''
    dlmtr = '?'
    for name in params:
        result = result + dlmtr + name
        result += '=%s' % params[name] if params[name] else result
        dlmtr = '&'
    return result
