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

import json
import logging
import os

from os.path import exists, expanduser


# Path to the file that stores the configuration
CONFIG_PATH = expanduser('~/.kamakirc')

# Name of a shell variable to bypass the CONFIG_PATH value
CONFIG_ENV = 'KAMAKI_CONFIG'

# The defaults also determine the allowed keys
CONFIG_DEFAULTS = {
    'apis': 'compute image storage cyclades',
    'token': '',
    'compute_url': 'https://okeanos.grnet.gr/api/v1',
    'image_url': 'https://okeanos.grnet.gr/plankton',
    'storage_url': 'https://plus.pithos.grnet.gr/v1',
    'storage_account': '',
    'storage_container': '',
    'test_token': ''
}


log = logging.getLogger('kamaki.config')


class ConfigError(Exception):
    pass


class Config(object):
    def __init__(self):
        self.path = os.environ.get(CONFIG_ENV, CONFIG_PATH)
        self.defaults = CONFIG_DEFAULTS
        
        d = self.read()
        for key, val in d.items():
            if key not in self.defaults:
                log.warning('Ignoring unknown config key "%s".', key)
        
        self.d = d
        self.overrides = {}
    
    def read(self):
        if not exists(self.path):
            return {}
        
        with open(self.path) as f:
            data = f.read()
        
        try:
            d = json.loads(data)
            assert isinstance(d, dict)
            return d
        except (ValueError, AssertionError):
            msg = '"%s" does not look like a kamaki config file.' % self.path
            raise ConfigError(msg)
    
    def write(self):
        self.read()     # Make sure we don't overwrite anything wrong
        with open(self.path, 'w') as f:
            data = json.dumps(self.d, indent=True)
            f.write(data)
    
    def items(self):
        for key, val in self.defaults.items():
            yield key, self.get(key)
    
    def get(self, key):
        if key in self.overrides:
            return self.overrides[key]
        if key in self.d:
            return self.d[key]
        return self.defaults.get(key, '')
    
    def set(self, key, val):
        if key not in self.defaults:
            log.warning('Ignoring unknown config key "%s".', key)
            return
        self.d[key] = val
        self.write()
    
    def delete(self, key):
        if key not in self.defaults:
            log.warning('Ignoring unknown config key "%s".', key)
            return
        self.d.pop(key, None)
        self.write()
    
    def override(self, key, val):
        assert key in self.defaults
        if val is not None:
            self.overrides[key] = val
