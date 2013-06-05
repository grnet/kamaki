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

from kamaki.cli.errors import CLISyntaxError

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
        #  'livetest_cli': 'livetest',
        #  'astakos_cli': 'snf-astakos'
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

        for section in self.sections():
            r = self._remote_name(section)
            if r:
                for k, v in self.items(section):
                    self.set_remote(r, k, v)
                self.remove_section(section)

    @staticmethod
    def _remote_name(full_section_name):
        matcher = match('remote "(\w+)"', full_section_name)
        return matcher.groups()[0] if matcher else None

    def rescue_old_file(self):
        lost_terms = []
        global_terms = DEFAULTS['global'].keys()
        translations = dict(
            config=dict(serv='', cmd='config'),
            history=dict(serv='', cmd='history'),
            pithos=dict(serv='pithos', cmd='file'),
            file=dict(serv='pithos', cmd='file'),
            store=dict(serv='pithos', cmd='file'),
            storage=dict(serv='pithos', cmd='file'),
            image=dict(serv='plankton', cmd='image'),
            plankton=dict(serv='plankton', cmd='image'),
            compute=dict(serv='compute', cmd=''),
            cyclades=dict(serv='compute', cmd='server'),
            server=dict(serv='compute', cmd='server'),
            flavor=dict(serv='compute', cmd='flavor'),
            network=dict(serv='compute', cmd='network'),
            astakos=dict(serv='astakos', cmd='user'),
            user=dict(serv='astakos', cmd='user'),
        )

        for s in self.sections():
            if s in ('global'):
                # global.url, global.token -->
                # remote.default.url, remote.default.token
                for term in set(self.keys(s)).difference(global_terms):
                    if term not in ('url', 'token'):
                        lost_terms.append('%s.%s = %s' % (
                            s, term, self.get(s, term)))
                        self.remove_option(s, term)
                        continue
                    gval = self.get(s, term)
                    cval = self.get_remote('default', term)
                    if gval and cval and (
                        gval.lower().strip('/') != cval.lower().strip('/')):
                            raise CLISyntaxError(
                                'Conflicting values for default %s' % term,
                                importance=2, details=[
                                    ' global.%s:  %s' % (term, gval),
                                    ' remote.default.%s:  %s' % (term, cval),
                                    'Please remove one of them manually:',
                                    ' /config delete global.%s' % term,
                                    ' or'
                                    ' /config delete remote.default.%s' % term,
                                    'and try again'])
                    elif gval:
                        print('... rescue %s.%s => remote.default.%s' % (
                            s, term, term))
                        self.set_remote('default', term, gval)
                    self.remove_option(s, term)
            # translation for <service> or <command> settings
            # <service> or <command group> settings --> translation --> global
            elif s in translations:

                if s in ('history',):
                    k = 'file'
                    v = self.get(s, k)
                    if v:
                        print('... rescue %s.%s => global.%s_%s' % (
                            s, k, s, k))
                        self.set('global', '%s_%s' % (s, k), v)
                        self.remove_option(s, k)

                trn = translations[s]
                for k, v in self.items(s, False):
                    if v and k in ('cli',):
                        print('... rescue %s.%s => global.%s_cli' % (
                            s, k, trn['cmd']))
                        self.set('global', 'file_cli', v)
                    elif v and k in ('url', 'token'):
                        print(
                            '... rescue %s.%s => remote.default.%s_%s' % (
                                s, k, trn['serv'], k))
                        self.set_remote('default', 'pithos_%s' % k, v)
                    elif v:
                        lost_terms.append('%s.%s = %s' % (s, k, v))
                self.remove_section(s)
        #  self.pretty_print()
        return lost_terms

    def pretty_print(self):
        for s in self.sections():
            print s
            for k, v in self.items(s):
                if isinstance(v, dict):
                    print '\t', k, '=> {'
                    for ki, vi in v.items():
                        print '\t\t', ki, '=>', vi
                    print('\t}')
                else:
                    print '\t', k, '=>', v

    def guess_version(self):
        checker = Config(self.path, with_defaults=False)
        sections = checker.sections()
        log.warning('Config file heuristic 1: global section ?')
        if 'global' in sections:
            if checker.get('global', 'url') or checker.get('global', 'token'):
                log.warning('..... config file has an old global section')
                return 2.0
        log.warning('........ nope')
        log.warning('Config file heuristic 2: at least 1 remote section ?')
        if 'remotes' in sections:
            for r in self.keys('remotes'):
                log.warning('... found remote "%s"' % r)
                return 3.0
        log.warning('........ nope')
        log.warning('All heuristics failed, cannot decide')
        return 0.0

    def get_remote(self, remote, option):
        """
        :param remote: (str) remote cloud alias

        :param option: (str) option in remote cloud section

        :returns: (str) the value assigned on this option

        :raises KeyError: if remote or remote's option does not exist
        """
        r = self.get('remotes', remote)
        if not r:
            raise KeyError('Remote "%s" does not exist' % remote)
        return r[option]

    def set_remote(self, remote, option, value):
        try:
            d = self.get('remotes', remote)
        except KeyError:
            pass
        d[option] = value
        self.set('remotes', remote, d)

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
        for r, d in self.items('remotes'):
            for k, v in d.items():
                self.set('remote "%s"' % r, k, v)
        self.remove_section('remotes')

        with open(self.path, 'w') as f:
            os.chmod(self.path, 0600)
            f.write(HEADER.lstrip())
            f.flush()
            RawConfigParser.write(self, f)
