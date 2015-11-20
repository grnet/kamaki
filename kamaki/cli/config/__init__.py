# Copyright 2011-2015 GRNET S.A. All rights reserved.
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
from sys import stdout, stderr

from collections import defaultdict
from ConfigParser import RawConfigParser, NoOptionError, NoSectionError, Error
from re import match

from kamaki.cli.errors import CLISyntaxError, CLIError
from kamaki.cli.utils import pref_enc, escape_ctrl_chars
from kamaki import __version__

try:
    from collections import OrderedDict
except ImportError:
    from kamaki.clients.utils.ordereddict import OrderedDict


class InvalidCloudNameError(Error):
    """A valid cloud name must pass through this regex: ([~@#$:.-\w]+)"""


log = getLogger(__name__)

# Path to the file that stores the configuration
CONFIG_PATH = os.path.expanduser('~/.kamakirc')
HISTORY_PATH = os.path.expanduser('~/.kamaki.history')
CLOUD_PREFIX = 'cloud'

# Name of a shell variable to bypass the CONFIG_PATH value
CONFIG_ENV = 'KAMAKI_CONFIG'

# Get default CA Certifications file path - created while packaging
try:
    from kamaki import defaults
    CACERTS_DEFAULT_PATH = getattr(defaults, 'CACERTS_DEFAULT_PATH', '')
except ImportError as ie:
    log.debug('ImportError while loading default certs: %s' % ie)
    CACERTS_DEFAULT_PATH = ''

version = ''
for c in '%s' % __version__:
    if c not in '0.123456789':
        break
    version += c
HEADER = '# Kamaki configuration file v%s\n' % version

DOCUMENTATION = OrderedDict()
DOCUMENTATION['global'] = OrderedDict()
DOCUMENTATION['global']['default_cloud'] = (
    'The default cloud, when there are more than one clouds'),
DOCUMENTATION['global']['colors'] = (
    'enable / disable console colors, requires "ansi-colors" (on / off)'),
DOCUMENTATION['global']['history_file'] = 'path to store kamaki history',
DOCUMENTATION['global']['history_limit'] = '#commands to keep in history',
DOCUMENTATION['global']['log_file'] = 'path to dumb kamaki logs',
DOCUMENTATION['global']['log_token'] = (
    'show user token in HTTP logs (insecure - on / off)'),
DOCUMENTATION['global']['log_data'] = (
    'show HTTP data (body) in logs (on / off)'),
DOCUMENTATION['global']['log_pid'] = 'show process id in HTTP logs (on / off)',
DOCUMENTATION['global']['ignore_ssl'] = (
    'allow insecure HTTP connections (on / off)'),
DOCUMENTATION['global']['ca_certs'] = (
    'path to CA certificates bundle (system depended)'),
DOCUMENTATION['global']['config_cli'] = 'CLI specs for config commands',
DOCUMENTATION['global']['history_cli'] = 'CLI specs for history commands',
DOCUMENTATION['global']['user_cli'] = 'CLI specs for user commands',
DOCUMENTATION['global']['quota_cli'] = 'CLI specs for quota commands',
DOCUMENTATION['global']['project_cli'] = 'CLI specs for project commands',
DOCUMENTATION['global']['resource_cli'] = 'CLI specs for resource commands',
DOCUMENTATION['global']['membership_cli'] = (
    'CLI specs for membership commands'),
DOCUMENTATION['global']['file_cli'] = 'CLI specs for file commands',
DOCUMENTATION['global']['container_cli'] = 'CLI specs for container commands',
DOCUMENTATION['global']['sharer_cli'] = 'CLI specs for sharer commands',
DOCUMENTATION['global']['group_cli'] = 'CLI specs for group commands',
DOCUMENTATION['global']['server_cli'] = 'CLI specs for server commands',
DOCUMENTATION['global']['flavor_cli'] = 'CLI specs for flavor commands',
DOCUMENTATION['global']['network_cli'] = 'CLI specs for network commands',
DOCUMENTATION['global']['subnet_cli'] = 'CLI specs for subnet commands',
DOCUMENTATION['global']['port_cli'] = 'CLI specs for port ommands',
DOCUMENTATION['global']['ip_cli'] = '\tCLI specs for ip commands',
DOCUMENTATION['global']['volume_cli'] = 'CLI specs for volume commands',
DOCUMENTATION['global']['snapshot_cli'] = 'CLI specs for snapshot commands',
DOCUMENTATION['global']['image_cli'] = 'CLI specs for image commands',
DOCUMENTATION['global']['imagecompute_cli'] = (
    'CLI specs for imagecompute commands'),
#  Optional command specs:
DOCUMENTATION['global']['service_cli'] = (
    '(hidden) CLI specs for service commands'),
DOCUMENTATION['global']['endpoint_cli'] = (
    '(hidden) CLI specs for endpoint list'),
DOCUMENTATION['global']['commission_cli'] = (
    '(hidden) CLI specs for commission commands'),
DOCUMENTATION['%s.<CLOUD NAME>' % CLOUD_PREFIX] = OrderedDict()
DOCUMENTATION['%s.<CLOUD NAME>' % CLOUD_PREFIX]['url'] = (
    'cloud authentication URL'),
DOCUMENTATION['%s.<CLOUD NAME>' % CLOUD_PREFIX]['token'] = (
    'user token for this cloud'),
DOCUMENTATION['%s.<CLOUD NAME>' % CLOUD_PREFIX]['pithos_container'] = (
    'default pithos container for this cloud (if not set, use pithos)'),
DOCUMENTATION['%s.<CLOUD NAME>' % CLOUD_PREFIX]['pithos_id'] = (
    'pithos user uuid (if not set, use the token user)'),

DEFAULTS = {
    'global': {
        'default_cloud': '',
        'colors': 'off',
        'log_file': os.path.expanduser('~/.kamaki.log'),
        'log_token': 'off',
        'log_data': 'off',
        'log_pid': 'off',
        'history_file': HISTORY_PATH,
        'history_limit': 0,
        'user_cli': 'astakos',
        'quota_cli': 'astakos',
        'resource_cli': 'astakos',
        'project_cli': 'astakos',
        'membership_cli': 'astakos',
        'file_cli': 'pithos',
        'container_cli': 'pithos',
        'sharer_cli': 'pithos',
        'group_cli': 'pithos',
        'server_cli': 'cyclades',
        'flavor_cli': 'cyclades',
        'network_cli': 'network',
        'subnet_cli': 'network',
        'port_cli': 'network',
        'ip_cli': 'network',
        'volume_cli': 'blockstorage',
        'snapshot_cli': 'blockstorage',
        'image_cli': 'image',
        'imagecompute_cli': 'image',
        'config_cli': 'config',
        'history_cli': 'history',
        'ignore_ssl': 'off',
        'scripts_cli': 'contrib.scripts',
        'ca_certs': CACERTS_DEFAULT_PATH,
        #  Optional command specs:
        #  'service_cli': 'astakos'
        #  'endpoint_cli': 'astakos'
        #  'commission_cli': 'astakos'
    },
    CLOUD_PREFIX: {
        # 'default': {
        #     'url': '',
        #     'token': ''
        #     'pithos_container': 'THIS IS DANGEROUS'
        #     'pithos_type': 'object-store',
        #     'pithos_version': 'v1',
        #     'cyclades_type': 'compute',
        #     'cyclades_version': 'v2.0',
        #     'plankton_type': 'image',
        #     'plankton_version': '',
        #     'astakos_type': 'identity',
        #     'astakos_version': 'v2.0'
        # }
    }
}


class Config(RawConfigParser):

    def __init__(self, path=None, with_defaults=False):
        RawConfigParser.__init__(self, dict_type=OrderedDict)
        self.path = path or os.environ.get(CONFIG_ENV, CONFIG_PATH)

        # Check if self.path is accessible
        abspath = os.path.abspath(self.path)
        if not os.path.exists(self.path):
            log.warning('Config file %s does not exist' % abspath)
        elif os.access(self.path, os.R_OK):
            if not os.access(self.path, os.W_OK):
                log.warning('Config file %s is not writable' % abspath)
        else:
            raise CLIError(
                'Config file %s is inaccessible' % abspath,
                importance=3, details=['No read permissions for this file'])

        self._overrides = defaultdict(dict)
        if with_defaults:
            self._load_defaults()
        self.read(self.path)

        for section in self.sections():
            r = self.cloud_name(section)
            if r:
                for k, v in self.items(section):
                    self.set_cloud(r, k, v)
                self.remove_section(section)

    @staticmethod
    def assert_option(option):
        if isinstance(option, unicode):
            try:
                option = str(option)
            except UnicodeError, ue:
                raise CLIError('Invalid config option %s' % option, details=[
                    'Illegal character(s) in config option name',
                    'Non-ascii characters are only allowed as values',
                    ue])

    @staticmethod
    def cloud_name(full_section_name):
        if not full_section_name.startswith(CLOUD_PREFIX + ' '):
            return None
        matcher = match(CLOUD_PREFIX + ' "([~@#$.:\-\w]+)"', full_section_name)
        if matcher:
            return matcher.groups()[0]
        else:
            icn = full_section_name[len(CLOUD_PREFIX) + 1:]
            raise InvalidCloudNameError('Invalid Cloud Name %s' % icn)

    def rescue_old_file(self, err=stderr):
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
            network=dict(serv='network', cmd='network'),
            astakos=dict(serv='astakos', cmd='user'),
            user=dict(serv='astakos', cmd='user'),
        )

        dc = 'default_' + CLOUD_PREFIX
        self.set('global', dc, self.get('global', dc) or 'default')
        for s in self.sections():
            if s in ('global', ):
                # global.url, global.token -->
                # cloud.default.url, cloud.default.token
                for term in set(self.keys(s)).difference(global_terms):
                    if term not in ('url', 'token'):
                        lost_terms.append('%s.%s = %s' % (
                            s, term, self.get(s, term)))
                        self.remove_option(s, term)
                        continue
                    gval = self.get(s, term)
                    default_cloud = self.get(
                        'global', 'default_cloud') or 'default'
                    try:
                        cval = self.get_cloud(default_cloud, term)
                    except KeyError:
                        cval = ''
                    if gval and cval and (
                            gval.lower().strip('/') != cval.lower().strip('/')
                            ):
                        raise CLISyntaxError(
                            'Conflicting values for default %s' % (term),
                            importance=2, details=[
                                ' global.%s:  %s' % (term, gval),
                                ' %s.%s.%s:  %s' % (
                                    CLOUD_PREFIX,
                                    default_cloud,
                                    term,
                                    cval),
                                'Please remove one of them manually:',
                                ' /config delete global.%s' % term,
                                ' or'
                                ' /config delete %s.%s.%s' % (
                                    CLOUD_PREFIX, default_cloud, term),
                                'and try again'])
                    elif gval:
                        err.write(u'... rescue %s.%s => %s.%s.%s\n' % (
                            s, term, CLOUD_PREFIX, default_cloud, term))
                        err.flush()
                        self.set_cloud('default', term, gval)
                    self.remove_option(s, term)
                for term, wrong, right in (
                        ('ip', 'cyclades', 'network'),
                        ('network', 'cyclades', 'network'),):
                    k = '%s_cli' % term
                    v = self.get(s, k)
                    if v in (wrong, ):
                        err.write('... change %s.%s value: `%s` => `%s`\n' % (
                            s, k, wrong, right))
                        err.flush()
                        self.set(s, k, right)
            # translation for <service> or <command> settings
            # <service> or <command group> settings --> translation --> global
            elif s in translations:

                if s in ('history',):
                    k = 'file'
                    v = self.get(s, k)
                    if v:
                        err.write(u'... rescue %s.%s => global.%s_%s\n' % (
                            s, k, s, k))
                        err.flush()
                        self.set('global', '%s_%s' % (s, k), v)
                        self.remove_option(s, k)

                trn = translations[s]
                for k, v in self.items(s, False):
                    if v and k in ('cli',):
                        err.write(u'... rescue %s.%s => global.%s_cli\n' % (
                            s, k, trn['cmd']))
                        err.flush()
                        self.set('global', '%s_cli' % trn['cmd'], v)
                    elif k in ('container',) and trn['serv'] in ('pithos',):
                        err.write(
                            u'... rescue %s.%s => %s.default.pithos_%s\n' % (
                                s, k, CLOUD_PREFIX, k))
                        err.flush()
                        self.set_cloud('default', 'pithos_%s' % k, v)
                    else:
                        lost_terms.append('%s.%s = %s' % (s, k, v))
                self.remove_section(s)
        #  self.pretty_print()
        return lost_terms

    def pretty_print(self, out=stdout):
        for s in self.sections():
            out.write(s)
            out.flush()
            for k, v in self.items(s):
                if isinstance(v, dict):
                    out.write(u'\t%s => {\n' % k)
                    out.flush()
                    for ki, vi in v.items():
                        out.write(u'\t\t%s => %s\n' % (ki, vi))
                        out.flush()
                    out.write(u'\t}\n')
                else:
                    out.write(u'\t %s => %s\n' % (k, v))
                out.flush()

    def guess_version(self):
        """
        :returns: (float) version of the config file or 0.9 if unrecognized
        """
        from kamaki.cli import logger
        # Ignore logs from "checker" logger
        logger.deactivate(__name__)
        checker = Config(self.path, with_defaults=False)
        logger.activate(__name__)

        sections = checker.sections()
        #  log.debug('Config file heuristic 1: old global section ?')
        if 'global' in sections:
            if checker.get('global', 'url') or checker.get('global', 'token'):
                log.debug('config file has an old global section')
                return 0.8
        #  log.debug('Config file heuristic 2: Any cloud sections ?')
        if CLOUD_PREFIX in sections:
            for r in self.keys(CLOUD_PREFIX):
                log.debug('found cloud "%s"' % r)
            ipv = self.get('global', 'ip_cli')
            if ipv in ('cyclades', ):
                    return 0.11
            netv = self.get('global', 'network_cli')
            if netv in ('cyclades', ):
                return 0.10
            return 0.12
        log.debug('All heuristics failed, cannot decide')
        return 0.12

    def get_cloud(self, cloud, option):
        """
        :param cloud: (str) cloud name

        :param option: (str) option in cloud section

        :returns: (str) the value assigned on this option

        :raises KeyError: if cloud or cloud's option does not exist
        """
        r = self.get(CLOUD_PREFIX, cloud) if cloud else None
        if not r:
            raise KeyError('Cloud "%s" does not exist' % cloud)
        return r[option]

    def set_cloud(self, cloud, option, value):
        try:
            d = self.get(CLOUD_PREFIX, cloud) or dict()
        except KeyError:
            d = dict()
        self.assert_option(option)
        d[option] = value
        self.set(CLOUD_PREFIX, cloud, d)

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
            for k, v in RawConfigParser.items(self, section):
                new_k, new_v = k, v
                if isinstance(k, basestring) and not isinstance(k, unicode):
                    new_k = k.decode(pref_enc)
                if isinstance(v, basestring) and not isinstance(v, unicode):
                    new_v = v.decode(pref_enc)
                d[new_k] = new_v
            # d.update(RawConfigParser.items(self, section))
        except NoSectionError:
            pass
        return d

    def reload(self):
        self = self.__init__(self.path)

    def get(self, section, option):
        """
        :param section: (str) HINT: for clouds, use cloud.<section>

        :param option: (str)

        :returns: (str) the value stored at section: {option: value}
        """
        value = self._overrides.get(section, {}).get(option)
        if value is not None:
            return value
        prefix = CLOUD_PREFIX + '.'
        if section.startswith(prefix):
            return self.get_cloud(section[len(prefix):], option)
        try:
            r = RawConfigParser.get(self, section, option)
            if isinstance(r, str):
                return r.decode(pref_enc, 'replace')
            return r
        except (NoSectionError, NoOptionError):
            return DEFAULTS.get(section, {}).get(option)

    def set(self, section, option, value):
        """
        :param section: (str) HINT: for remotes use cloud.<section>

        :param option: (str)

        :param value: str
        """
        self.assert_option(option)
        prefix = CLOUD_PREFIX + '.'
        if section.startswith(prefix):
            cloud = self.cloud_name(
                CLOUD_PREFIX + ' "' + section[len(prefix):] + '"')
            return self.set_cloud(cloud, option, value)
        if section not in RawConfigParser.sections(self):
            self.add_section(section)
        return RawConfigParser.set(self, section, option, value)

    def remove_option(self, section, option, also_remove_default=False):
        try:
            if also_remove_default:
                DEFAULTS[section].pop(option)
            RawConfigParser.remove_option(self, section, option)
        except (NoSectionError, KeyError):
            pass

    def remove_from_cloud(self, cloud, option):
        d = self.get(CLOUD_PREFIX, cloud)
        if isinstance(d, dict):
            d.pop(option)

    def keys(self, section, include_defaults=True):
        d = self._get_dict(section, include_defaults)
        return d.keys()

    def items(self, section, include_defaults=True):
        d = self._get_dict(section, include_defaults)
        return d.items()

    def override(self, section, option, value):
        self._overrides[section][option] = value

    def safe_to_print(self):
        dump = u'[global]\n'
        for k, v in self.items('global', include_defaults=False):
            dump += u'%s = %s\n' % (escape_ctrl_chars(k), escape_ctrl_chars(v))
        for r, d in self.items(CLOUD_PREFIX, include_defaults=False):
            dump += u'\n[%s "%s"]\n' % (CLOUD_PREFIX, escape_ctrl_chars(r))
            for k, v in d.items():
                dump += u'%s = %s\n' % (
                    escape_ctrl_chars(k), escape_ctrl_chars(v))
        return dump

    def write(self):
        with open(self.path, mode='w') as f:
            os.chmod(self.path, 0600)
            f.write(HEADER.lstrip())
            f.write(self.safe_to_print().encode(pref_enc, 'replace'))
