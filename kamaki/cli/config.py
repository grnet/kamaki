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

import os
from logging import getLogger

from collections import defaultdict
from ConfigParser import RawConfigParser, NoOptionError, NoSectionError
from re import match

try:
    from collections import OrderedDict
except ImportError:
    from kamaki.clients.utils.ordereddict import OrderedDict


log = getLogger(__name__)

# Path to the file that stores the configuration
CONFIG_PATH = os.path.expanduser('~/.kamakirc')
HISTORY_PATH = os.path.expanduser('~/.kamaki.history')

# Name of a shell variable to bypass the CONFIG_PATH value
CONFIG_ENV = 'KAMAKI_CONFIG'

HEADER = """
# Kamaki configuration file v3 (kamaki >= v0.9)
"""

DEFAULTS = {
    'global': {
        'colors': 'off',
        'log_file': os.path.expanduser('~/.kamaki.log'),
        'log_token': 'off',
        'log_data': 'off',
        'max_threads': 7,
        'history_file': HISTORY_PATH,
        'user_cli': 'astakos',
        'file_cli': 'pithos',
        'server_cli': 'cyclades',
        'flavor_cli': 'cyclades',
        'network_cli': 'cyclades',
        'image_cli': 'image',
        'config_cli': 'config',
        'history_cli': 'history'
        #  Optional command specs:
        #  'livetest': 'livetest',
        #  'astakos': 'snf-astakos'
    },
    'remotes':
    {
        'default': {
            'url': '',
            'token': ''
            #'pithos_type': 'object-store',
            #'pithos_version': 'v1',
            #'cyclades_type': 'compute',
            #'cyclades_version': 'v2.0',
            #'plankton_type': 'image',
            #'plankton_version': '',
            #'astakos_type': 'identity',
            #'astakos_version': 'v2.0'
        }
    }
}


class Config(RawConfigParser):
    def __init__(self, path=None, with_defaults=True):
        RawConfigParser.__init__(self, dict_type=OrderedDict)
        self.path = path or os.environ.get(CONFIG_ENV, CONFIG_PATH)
        self._overrides = defaultdict(dict)
        if with_defaults:
            self._load_defaults()
        self.read(self.path)

    @staticmethod
    def _remote_name(full_section_name):
        matcher = match('remote "(\w+)"', full_section_name)
        return matcher.groups()[0] if matcher else None

    def guess_version(self):
        checker = Config(self.path, with_defaults=False)
        sections = checker.sections()
        log.warning('Config file heuristic 1: global section ?')
        v = 0.0
        if 'global' in sections:
            if checker.get('global', 'url') or checker.get('global', 'token'):
                log.warning('..... config file has an old global section')
                v = 2.0
        log.warning('Config file heuristic 2: at least 1 remote section ?')
        for section in sections:
            if self._remote_name(section):
                log.warning('... found %s section' % section)
                v = 3.0
        log.warning('All heuristics failed, cannot decide')
        del checker
        return v

    def _load_defaults(self):
        for section, options in DEFAULTS.items():
            for option, val in options.items():
                self.set(section, option, val)

    def _get_dict(self, section, include_defaults=True):
        try:
            d = dict(DEFAULTS[section]) if include_defaults else {}
        except KeyError:
            d = {}
        try:
            d.update(RawConfigParser.items(self, section))
        except NoSectionError:
            pass
        return d

    def reload(self):
        self = self.__init__(self.path)

    def get(self, section, option):
        value = self._overrides.get(section, {}).get(option)
        if value is not None:
            return value

        try:
            return RawConfigParser.get(self, section, option)
        except (NoSectionError, NoOptionError):
            return DEFAULTS.get(section, {}).get(option)

    def set(self, section, option, value):
        if section not in RawConfigParser.sections(self):
            self.add_section(section)
        RawConfigParser.set(self, section, option, value)

    def remove_option(self, section, option, also_remove_default=False):
        try:
            if also_remove_default:
                DEFAULTS[section].pop(option)
            RawConfigParser.remove_option(self, section, option)
        except NoSectionError:
            pass

    def keys(self, section, include_defaults=True):
        d = self._get_dict(section, include_defaults)
        return d.keys()

    def items(self, section, include_defaults=True):
        d = self._get_dict(section, include_defaults)
        return d.items()

    def override(self, section, option, value):
        self._overrides[section][option] = value

    def write(self):
        with open(self.path, 'w') as f:
            os.chmod(self.path, 0600)
            f.write(HEADER.lstrip())
            f.flush()
            RawConfigParser.write(self, f)
