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
# or implied, of GRNET S.A.command

from kamaki.cli.logger import get_logger
from kamaki.cli.utils import print_json, print_items
from kamaki.cli.argument import FlagArgument

log = get_logger(__name__)


def DontRaiseKeyError(foo):
    def wrap(*args, **kwargs):
        try:
            return foo(*args, **kwargs)
        except KeyError:
            return None
    return wrap


def addLogSettings(foo):
    def wrap(self, *args, **kwargs):
        try:
            return foo(self, *args, **kwargs)
        finally:
            self._set_log_params()
            self._update_max_threads
    return wrap


class _command_init(object):

    def __init__(self, arguments={}, auth_base=None, cloud=None):
        if hasattr(self, 'arguments'):
            arguments.update(self.arguments)
        if isinstance(self, _optional_output_cmd):
            arguments.update(self.oo_arguments)
        if isinstance(self, _optional_json):
            arguments.update(self.oj_arguments)
        self.arguments = dict(arguments)
        try:
            self.config = self['config']
        except KeyError:
            pass
        self.auth_base = auth_base or getattr(self, 'auth_base', None)
        self.cloud = cloud or getattr(self, 'cloud', None)

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

    def _set_log_params(self):
        try:
            self.client.LOG_TOKEN, self.client.LOG_DATA = (
                self['config'].get_global('log_token').lower() == 'on',
                self['config'].get_global('log_data').lower() == 'on')
        except Exception as e:
            log.debug('Failed to read custom log settings:'
                '%s\n defaults for token and data logging are off' % e)

    def _update_max_threads(self):
        if getattr(self, 'client', None):
            max_threads = int(self['config'].get_global('max_threads'))
            assert max_threads > 0
            self.client.MAX_THREADS = max_threads

    def _safe_progress_bar(self, msg, arg='progress_bar'):
        """Try to get a progress bar, but do not raise errors"""
        try:
            progress_bar = self.arguments[arg]
            gen = progress_bar.get_generator(msg)
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


class _optional_output_cmd(object):

    oo_arguments = dict(
        with_output=FlagArgument('show response headers', ('--with-output')),
        json_output=FlagArgument('show headers in json', ('-j', '--json'))
    )

    def _optional_output(self, r):
        if self['json_output']:
            print_json(r)
        elif self['with_output']:
            print_items([r] if isinstance(r, dict) else r)


class _optional_json(object):

    oj_arguments = dict(
        json_output=FlagArgument('show headers in json', ('-j', '--json'))
    )

    def _print(self, output, print_method=print_items, **print_method_kwargs):
        if self['json_output']:
            print_json(output)
        else:
            print_method(output, **print_method_kwargs)
