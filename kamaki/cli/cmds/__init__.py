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
# or implied, of GRNET S.A.command

from sys import stdin, stdout, stderr, exit
from traceback import format_exc

from kamaki.cli.logger import get_logger
from kamaki.cli.utils import (
    print_list, print_dict, print_json, print_items, ask_user, pref_enc,
    filter_dicts_by_dict)
from kamaki.cli.argument import ValueArgument, ProgressBarArgument
from kamaki.cli.errors import CLIInvalidArgument, CLIBaseUrlError
from kamaki.cli.cmds import errors
from kamaki.clients.utils import escape_ctrl_chars


log = get_logger(__name__)


def dont_raise(*errs):
    def decorator(func):
        def wrap(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except errs as e:
                log.debug('Suppressed error %s while calling %s(%s)' % (
                    e, func.__name__, ','.join(['%s' % i for i in args] + [
                        ('%s=%s' % items) for items in kwargs.items()])))
                log.debug(format_exc(e))
                return None
        wrap.__name__ = func.__name__
        return wrap
    return decorator


def client_log(func):
    def wrap(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        finally:
            self._set_log_params()
    wrap.__name__ = func.__name__
    return wrap


def fall_back(func):
    def wrap(self, inp):
        try:
            inp = func(self, inp)
        except Exception as e:
            log.warning('Error while running %s: %s' % (func, e))
            log.warning('Kamaki will use original data to go on')
        finally:
            return inp
    wrap.__name__ = func.__name__
    return wrap


class CommandInit(object):

    # self.arguments (dict) contains all non-positional arguments
    # self.required (list or tuple) contains required argument keys
    #     if it is a list, at least one of these arguments is required
    #     if it is a tuple, all arguments are required
    #     Lists and tuples can nest other lists and/or tuples

    def __init__(
            self,
            arguments={}, astakos=None, cloud=None,
            _in=None, _out=None, _err=None):
        self._in, self._out, self._err = (
            _in or stdin, _out or stdout, _err or stderr)
        self.required = getattr(self, 'required', None)
        if hasattr(self, 'arguments'):
            arguments.update(self.arguments)
        if isinstance(self, OptionalOutput):
            arguments.update(self.oo_arguments)
        if isinstance(self, NameFilter):
            arguments.update(self.nf_arguments)
        if isinstance(self, IDFilter):
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
        self.astakos = astakos or getattr(self, 'astakos', None)
        self.cloud = cloud or getattr(self, 'cloud', None)

    def get_client(self, cls, service):
        self.cloud = getattr(self, 'cloud', 'default')
        URL, TOKEN = self._custom_url(service), self._custom_token(service)
        if not all([URL, TOKEN]):
            astakos = getattr(self, 'astakos', None)
            if astakos:
                URL = URL or astakos.get_endpoint_url(
                    self._custom_type(service) or cls.service_type,
                    self._custom_version(service))
                TOKEN = TOKEN or astakos.token
            else:
                raise CLIBaseUrlError(service=service)
        return cls(URL, TOKEN)

    @errors.Astakos.project_id
    def _project_id_exists(self, project_id):
        self.astakos.get_client().get_project(project_id)

    @dont_raise(UnicodeError)
    def write(self, s):
        self._out.write(s.encode(pref_enc, 'replace'))
        self._out.flush()

    def writeln(self, s=''):
        self.write('%s\n' % s)

    def error(self, s=''):
        esc_s = escape_ctrl_chars(s)
        self._err.write(('%s\n' % esc_s).encode(pref_enc, 'replace'))
        self._err.flush()

    def print_list(self, *args, **kwargs):
        kwargs.setdefault('out', self._out)
        return print_list(*args, **kwargs)

    def print_dict(self, *args, **kwargs):
        kwargs.setdefault('out', self)
        return print_dict(*args, **kwargs)

    def print_json(self, *args, **kwargs):
        kwargs.setdefault('out', self)
        return print_json(*args, **kwargs)

    def print_items(self, *args, **kwargs):
        kwargs.setdefault('out', self)
        return print_items(*args, **kwargs)

    def ask_user(self, *args, **kwargs):
        kwargs.setdefault('user_in', self._in)
        kwargs.setdefault('out', self)
        return ask_user(*args, **kwargs)

    @dont_raise(KeyError)
    def _custom_url(self, service):
        return self.config.get_cloud(self.cloud, '%s_url' % service)

    @dont_raise(KeyError)
    def _custom_token(self, service):
        return self.config.get_cloud(self.cloud, '%s_token' % service)

    @dont_raise(KeyError)
    def _custom_type(self, service):
        return self.config.get_cloud(self.cloud, '%s_type' % service)

    @dont_raise(KeyError)
    def _custom_version(self, service):
        return self.config.get_cloud(self.cloud, '%s_version' % service)

    def _uuids2usernames(self, uuids):
        return self.astakos.post_user_catalogs(uuids)

    def _usernames2uuids(self, username):
        return self.astakos.post_user_catalogs(displaynames=username)

    def _uuid2username(self, uuid):
        return self._uuids2usernames([uuid]).get(uuid, None)

    def _username2uuid(self, username):
        return self._usernames2uuids([username]).get(username, None)

    def _set_log_params(self):
        if not getattr(self, 'client', None):
            return
        try:
            self.client.LOG_TOKEN = self.client.LOG_TOKEN or (
                self['config'].get('global', 'log_token').lower() == 'on')
        except Exception as e:
            log.debug('Failed to read custom log_token setting:'
                      '%s\n default for log_token is off' % e)
        try:
            self.client.LOG_DATA = self.client.LOG_DATA or (
                self['config'].get('global', 'log_data').lower() == 'on')
        except Exception as e:
            log.debug('Failed to read custom log_data setting:'
                      '%s\n default for log_data is off' % e)
        try:
            self.client.LOG_PID = self.client.LOG_PID or (
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

    formats = dict(json=print_json)

    def ___init__(self, *args, **kwargs):
        super(OutputFormatArgument, self).___init__(*args, **kwargs)
        self.value = None

    def value(self, newvalue):
        if not newvalue:
            return
        elif newvalue.lower() in self.formats:
            self.value = newvalue.lower()
        else:
            raise CLIInvalidArgument(
                'Invalid value %s for argument %s' % (newvalue, self.lvalue),
                details=['Valid output formats: %s' % ', '.join(self.formats)])


class OptionalOutput(object):

    oo_arguments = dict(
        output_format=OutputFormatArgument(
            'Show output in chosen output format (%s)' % ', '.join(
                OutputFormatArgument.formats),
            '--output-format'),
    )

    def print_(self, output, print_method=print_items, **print_method_kwargs):
        if self['output_format']:
            func = OutputFormatArgument.formats[self['output_format']]
            func(output, out=self)
        else:
            print_method_kwargs.setdefault('out', self)
            print_method(output, **print_method_kwargs)


class NameFilter(object):

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


class IDFilter(object):

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


class Wait(object):
    wait_arguments = dict(
        progress_bar=ProgressBarArgument(
            'do not show progress bar', ('-N', '--no-progress-bar'), False)
    )

    def wait(
            self, service, service_id, status_method, status,
            countdown=True, timeout=60, msg='still', update_cb=None):
        (progress_bar, wait_gen) = self._safe_progress_bar(
            '%s %s status %s %s' % (service, service_id, msg, status),
            countdown=countdown, timeout=timeout)
        wait_step = None
        if wait_gen:
            wait_step = wait_gen(timeout)
            wait_step.next()

        def wait_cb(item_details):
            if wait_step:
                if update_cb:
                    progress_bar.bar.goto(update_cb(item_details))
                else:
                    wait_step.next()

        try:
            item_details = status_method(
                service_id, status, max_wait=timeout, wait_cb=wait_cb)
            if item_details:
                self.error('')
                self.error('%s %s status: %s' % (
                    service, service_id, item_details['status']))
            else:
                exit("Operation timed out")
        except KeyboardInterrupt:
            self.error(' - canceled')
        finally:
            self._safe_progress_bar_finish(progress_bar)
