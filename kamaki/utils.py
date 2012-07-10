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

def print_addresses(addresses, margin):
    for address in addresses:
        if address['id'] == 'public':
            net = 'public'
        else:
            net = '%s/%s' % (address['id'], address['network_id'])
        print '%s:' % net.rjust(margin + 4)

        ether = address.get('mac', None)
        if ether:
            print '%s: %s' % ('ether'.rjust(margin + 8), ether)

        firewall = address.get('firewallProfile', None)
        if firewall:
            print '%s: %s' % ('firewall'.rjust(margin + 8), firewall)

        for ip in address.get('values', []):
            key = 'inet' if ip['version'] == 4 else 'inet6'
            print '%s: %s' % (key.rjust(margin + 8), ip['addr'])

def print_dict(d, exclude=()):
    if not d:
        return
    margin = max(len(key) for key in d) + 1

    for key, val in sorted(d.items()):
        if key in exclude:
            continue

        #if key == 'addresses':
        #    print '%s:' % 'addresses'.rjust(margin)
        #    print_addresses(val.get('values', []), margin)
        #    continue
        if key == 'attachments':
            print '%s:' % 'attachments'.rjust(margin)
            print_addresses(val.get('values', []), margin)
            continue
        elif key == 'servers':
            val = ', '.join(unicode(x) for x in val['values'])
        elif isinstance(val, dict):
            if val.keys() == ['values']:
                val = val['values']
            print '%s:' % key.rjust(margin)
            for key, val in val.items():
                print '%s: %s' % (key.rjust(margin + 4), val)
            continue

        print '%s: %s' % (key.rjust(margin), val)


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

def dict_from_args(*args):
    return {args[i]:args[i+1] for i in range(0, len(args)/2)}

