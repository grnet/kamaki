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

def matches(val1, val2, exactMath=True):
    """Case Insenstive match"""
    if exactMath:
        return True if val1.lower() == val2.lower() else False
    else:
        return True if val1.lower().startswith(val2.lower()) else False

def filter_out(d, prefix, exactMatch = False):
    """@return a dict that contains the entries of d that are NOT prefixed with prefic
    """
    ret = {}
    for key, val in d.items():
        if not matches(key, prefix, exactMath = exactMatch):
            ret[key] = val
    return ret

def filter_in(d, prefix, exactMatch = False):
    """@return a dict that contains only the entries of d that are prefixed with prefix
    """
    ret = {}
    for key, val in d.items():
        if matches(key, prefix, exactMath = exactMatch):
            ret[key] = val
    return ret
    
def prefix_keys(d, prefix):
    """@return a sallow copy of d with all its keys prefixed with prefix
    """
    ret = {}
    for key, val in d.items():
        ret[prefix+key] = val
    return ret

def path4url(*args):
    """@return a string with all args in the form /arg1/arg2/...
       @param args must be strings
    """
    path = ''
    for arg in args:
        path = path + '/' + unicode(arg)
    return path

def params4url(params):
    """@return a string with all params in the form ?key1=val1&key2=val2&...
            e.g. input
                {'key1':'val1', 'key2':None, 'key3':'val3'}
            will return
                ?key1=val1&key2&key3=val3
       @param should be a dict.
            Use params['somekey']=None for params that will apear without 
            a value at the final string
    """
    assert(type(params) is dict)
    result = ''
    dlmtr = '?'
    for name in params:
        result = result + dlmtr + name
        result = result + '=' + unicode(params[name]) if params[name] is not None else result
        dlmtr = '&'
    return result

def list2str(alist, seperator=','):
    """@return a string of comma seperated elements of the list"""
    ret = ''
    slist = sorted(alist)
    for item in slist:
        if 0 == slist.index(item):
            ret = unicode(item)
        else:
            ret += seperator+unicode(item)
    return ret

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

