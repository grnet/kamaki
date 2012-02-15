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

from collections import defaultdict
from ConfigParser import RawConfigParser, NoOptionError, NoSectionError

from .utils import OrderedDict


HEADER = """
# Kamaki configuration file
"""

DEFAULTS = {
    'global': {
        'colors': 'on',
        'token': ''
    },
    'compute': {
        'enable': 'on',
        'cyclades_extensions': 'on',
        'url': 'https://okeanos.grnet.gr/api/v1.1',
        'token': ''
    },
    'image': {
        'enable': 'on',
        'url': 'https://okeanos.grnet.gr/plankton',
        'token': ''
    },
    'storage': {
        'enable': 'on',
        'pithos_extensions': 'on',
        'url': 'https://plus.pithos.grnet.gr/v1',
        'account': '',
        'container': '',
        'token': ''
    }
}


class Config(RawConfigParser):
    def __init__(self, path=None):
        RawConfigParser.__init__(self, dict_type=OrderedDict)
        self.path = path
        self._overrides = defaultdict(dict)
        self.read(path)
    
    def sections(self):
        return DEFAULTS.keys()
    
    def get(self, section, option):
        value = self._overrides.get(section, {}).get(option)
        if value is not None:
            return value
        
        try:
            return RawConfigParser.get(self, section, option)
        except (NoSectionError, NoOptionError) as e:
            return DEFAULTS.get(section, {}).get(option)
    
    def set(self, section, option, value):
        if section not in RawConfigParser.sections(self):
            self.add_section(section)
        RawConfigParser.set(self, section, option, value)
    
    def remove_option(self, section, option):
        try:
            RawConfigParser.remove_option(self, section, option)
        except NoSectionError:
            pass
    
    def items(self, section, include_defaults=False):
        d = dict(DEFAULTS[section]) if include_defaults else {}
        try:
            d.update(RawConfigParser.items(self, section))
        except NoSectionError:
            pass
        return d.items()
    
    def override(self, section, option, value):
        self._overrides[section][option] = value
    
    def write(self):
        with open(self.path, 'w') as f:
            f.write(HEADER.lstrip())
            RawConfigParser.write(self, f)
