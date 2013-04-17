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

from kamaki import logger

logger.add_file_logger('cli', __name__, filename=logger.get_log_filename())
sendlog = logger.get_logger('cli')


class _command_init(object):

    def __init__(self, arguments={}):
        if hasattr(self, 'arguments'):
            arguments.update(self.arguments)
        self.arguments = dict(arguments)
        try:
            self.config = self['config']
            #self.config = self.get_argument('config')
        except KeyError:
            pass

    def _set_log_params(self):
        try:
            self.client.LOG_TOKEN, self.client.LOG_DATA = (
                self['config'].get('global', 'log_token') == 'on',
                self['config'].get('global', 'log_data') == 'on')
        except Exception as e:
            sendlog.warning('Failed to read custom log settings: %s' % e)
            sendlog.warning('\tdefaults for token and data logging are off')
            pass

    def _update_max_threads(self):
        try:
            max_threads = int(self['config'].get('global', 'max_threads'))
            assert max_threads > 0
            self.client.MAX_THREADS = max_threads
        except Exception as e:
            sendlog.warning('Failed to read custom thread settings: %s' % e)
            sendlog.warning(
                '\tdefault for max threads is %s' % self.client.MAX_THREADS)
            pass

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
