# Copyright 2011-2013 GRNET S.A. All rights reserved.
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
# or implied, of GRNET S.A.command

from kamaki.cli.logger import get_logger
from kamaki.cli.utils import (
    print_list, print_dict, print_json, print_items, ask_user,
    filter_dicts_by_dict)
from kamaki.cli.argument import FlagArgument, ValueArgument
from kamaki.cli.errors import CLIInvalidArgument
from sys import stdin, stdout, stderr

log = get_logger(__name__)


def DontRaiseKeyError(func):
    def wrap(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except KeyError:
            return None
    return wrap


def addLogSettings(func):
    def wrap(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        finally:
            self._set_log_params()
    return wrap


class _command_init(object):

    # self.arguments (dict) contains all non-positional arguments
    # self.required (list or tuple) contains required argument keys
    #     if it is a list, at least one of these arguments is required
    #     if it is a tuple, all arguments are required
    #     Lists and tuples can nest other lists and/or tuples

    def __init__(
            self,
            arguments={}, auth_base=None, cloud=None,
            _in=None, _out=None, _err=None):
        self._in, self._out, self._err = (
            _in or stdin, _out or stdout, _err or stderr)
        self.required = getattr(self, 'required', None)
        if hasattr(self, 'arguments'):
            arguments.update(self.arguments)
        if isinstance(self, _optional_output_cmd):
            arguments.update(self.oo_arguments)
        if isinstance(self, _optional_json):
            arguments.update(self.oj_arguments)
        if isinstance(self, _name_filter):
            arguments.update(self.nf_arguments)
        if isinstance(self, _id_filter):
            arguments.update(self.if_arguments)
        try:
            arguments.update(self.wait_arguments)
        except AttributeError:
            pass
        self.arguments = dict(arguments)
        try:
            self.config = self['config']
        except KeyError:
            pass
        self.auth_base = auth_base or getattr(self, 'auth_base', None)
        self.cloud = cloud or getattr(self, 'cloud', None)

    def write(self, s):
        self._out.write('%s' % s)
        self._out.flush()

    def writeln(self, s=''):
        self.write('%s\n' % s)

    def error(self, s=''):
        self._err.write('%s\n' % s)
        self._err.flush()

    def print_list(self, *args, **kwargs):
        kwargs.setdefault('out', self._out)
        return print_list(*args, **kwargs)

    def print_dict(self, *args, **kwargs):
        kwargs.setdefault('out', self._out)
        return print_dict(*args, **kwargs)

    def print_json(self, *args, **kwargs):
        kwargs.setdefault('out', self._out)
        return print_json(*args, **kwargs)

    def print_items(self, *args, **kwargs):
        kwargs.setdefault('out', self._out)
        return print_items(*args, **kwargs)

    def ask_user(self, *args, **kwargs):
        kwargs.setdefault('user_in', self._in)
        kwargs.setdefault('out', self._out)
        return ask_user(*args, **kwargs)

    @DontRaiseKeyError
    def _custom_url(self, service):
        return self.config.get_cloud(self.cloud, '%s_url' % service)

    @DontRaiseKeyError
    def _custom_token(self, service):
        return self.config.get_cloud(self.cloud, '%s_token' % service)

    @DontRaiseKeyError
    def _custom_type(self, service):
        return self.config.get_cloud(self.cloud, '%s_type' % service)

    @DontRaiseKeyError
    def _custom_version(self, service):
        return self.config.get_cloud(self.cloud, '%s_version' % service)

    def _uuids2usernames(self, uuids):
        return self.auth_base.post_user_catalogs(uuids)

    def _usernames2uuids(self, username):
        return self.auth_base.post_user_catalogs(displaynames=username)

    def _uuid2username(self, uuid):
        return self._uuids2usernames([uuid]).get(uuid, None)

    def _username2uuid(self, username):
        return self._usernames2uuids([username]).get(username, None)

    def _set_log_params(self):
        try:
            self.client.LOG_TOKEN = (
                self['config'].get('global', 'log_token').lower() == 'on')
        except Exception as e:
            log.debug('Failed to read custom log_token setting:'
                '%s\n default for log_token is off' % e)
        try:
            self.client.LOG_DATA = (
                self['config'].get('global', 'log_data').lower() == 'on')
        except Exception as e:
            log.debug('Failed to read custom log_data setting:'
                '%s\n default for log_data is off' % e)
        try:
            self.client.LOG_PID = (
                self['config'].get('global', 'log_pid').lower() == 'on')
        except Exception as e:
            log.debug('Failed to read custom log_pid setting:'
                '%s\n default for log_pid is off' % e)

    def _safe_progress_bar(
            self, msg, arg='progress_bar', countdown=False, timeout=100):
        """Try to get a progress bar, but do not raise errors"""
        try:
            progress_bar = self.arguments[arg]
            progress_bar.file = self._err
            gen = progress_bar.get_generator(
                msg, countdown=countdown, timeout=timeout)
        except Exception:
            return (None, None)
        return (progress_bar, gen)

    def _safe_progress_bar_finish(self, progress_bar):
        try:
            progress_bar.finish()
        except Exception:
            pass

    def __getitem__(self, argterm):
        """
        :param argterm: (str) the name/label of an argument in self.arguments

        :returns: the value of the corresponding Argument (not the argument
            object)

        :raises KeyError: if argterm not in self.arguments of this object
        """
        return self.arguments[argterm].value

    def __setitem__(self, argterm, arg):
        """Install an argument as argterm
        If argterm points to another argument, the other argument is lost

        :param argterm: (str)

        :param arg: (Argument)
        """
        if not hasattr(self, 'arguments'):
            self.arguments = {}
        self.arguments[argterm] = arg

    def get_argument_object(self, argterm):
        """
        :param argterm: (str) the name/label of an argument in self.arguments

        :returns: the arument object

        :raises KeyError: if argterm not in self.arguments of this object
        """
        return self.arguments[argterm]

    def get_argument(self, argterm):
        """
        :param argterm: (str) the name/label of an argument in self.arguments

        :returns: the value of the arument object

        :raises KeyError: if argterm not in self.arguments of this object
        """
        return self[argterm]


#  feature classes - inherit them to get special features for your commands


class OutputFormatArgument(ValueArgument):
    """Accepted output formats: json (default)"""

    formats = ('json', )

    def ___init__(self, *args, **kwargs):
        super(OutputFormatArgument, self).___init__(*args, **kwargs)

    @property
    def value(self):
        return getattr(self, '_value', None)

    @value.setter
    def value(self, newvalue):
        if not newvalue:
            self._value = self.default
        elif newvalue.lower() in self.formats:
            self._value = newvalue.lower
        else:
            raise CLIInvalidArgument(
                'Invalid value %s for argument %s' % (
                    newvalue, self.lvalue),
                details=['Valid output formats: %s' % ', '.join(self.formats)])


class _optional_output_cmd(object):

    oo_arguments = dict(
        with_output=FlagArgument('show response headers', ('--with-output')),
        json_output=FlagArgument(
            'show headers in json (DEPRECATED from v0.12,'
            '  please use --output-format=json instead)', ('-j', '--json'))
    )

    def _optional_output(self, r):
        if self['json_output']:
            print_json(r, out=self._out)
        elif self['with_output']:
            print_items([r] if isinstance(r, dict) else r, out=self._out)


class _optional_json(object):

    oj_arguments = dict(
        output_format=OutputFormatArgument(
            'Show output in chosen output format (%s)' % ', '.join(
                OutputFormatArgument.formats),
            '--output-format'),
        json_output=FlagArgument(
            'show output in json (DEPRECATED from v0.12,'
            ' please use --output-format instead)', ('-j', '--json'))
    )

    def _print(self, output, print_method=print_items, **print_method_kwargs):
        if self['json_output'] or self['output_format']:
            print_json(output, out=self._out)
        else:
            print_method_kwargs.setdefault('out', self._out)
            print_method(output, **print_method_kwargs)


class _name_filter(object):

    nf_arguments = dict(
        name=ValueArgument('filter by name', '--name'),
        name_pref=ValueArgument(
            'filter by name prefix (case insensitive)', '--name-prefix'),
        name_suff=ValueArgument(
            'filter by name suffix (case insensitive)', '--name-suffix'),
        name_like=ValueArgument(
            'print only if name contains this (case insensitive)',
            '--name-like')
    )

    def _non_exact_name_filter(self, items):
        np, ns, nl = self['name_pref'], self['name_suff'], self['name_like']
        return [item for item in items if (
            (not np) or (item['name'] or '').lower().startswith(
                np.lower())) and (
            (not ns) or (item['name'] or '').lower().endswith(
                ns.lower())) and (
            (not nl) or nl.lower() in (item['name'] or '').lower())]

    def _exact_name_filter(self, items):
        return filter_dicts_by_dict(items, dict(name=self['name'] or '')) if (
            self['name']) else items

    def _filter_by_name(self, items):
        return self._non_exact_name_filter(self._exact_name_filter(items))


class _id_filter(object):

    if_arguments = dict(
        id=ValueArgument('filter by id', '--id'),
        id_pref=ValueArgument(
            'filter by id prefix (case insensitive)', '--id-prefix'),
        id_suff=ValueArgument(
            'filter by id suffix (case insensitive)', '--id-suffix'),
        id_like=ValueArgument(
            'print only if id contains this (case insensitive)', '--id-like')
    )

    def _non_exact_id_filter(self, items):
        np, ns, nl = self['id_pref'], self['id_suff'], self['id_like']
        return [item for item in items if (
            (not np) or (
                '%s' % item['id']).lower().startswith(np.lower())) and (
            (not ns) or ('%s' % item['id']).lower().endswith(ns.lower())) and (
            (not nl) or nl.lower() in ('%s' % item['id']).lower())]

    def _exact_id_filter(self, items):
        return filter_dicts_by_dict(items, dict(id=self['id'])) if (
            self['id']) else items

    def _filter_by_id(self, items):
        return self._non_exact_id_filter(self._exact_id_filter(items))
