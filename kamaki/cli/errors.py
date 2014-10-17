# Copyright 2013 GRNET S.A. All rights reserved.
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

from kamaki.cli.logger import get_logger

log = get_logger('kamaki.cli')


class CLIError(Exception):

    def __init__(self, message, details=[], importance=0):
        """
        :param message: is the main message of the Error
        :param defaults: is a list of previous errors
        :param importance: of the output for the user (0, 1, 2, 3)
        """
        message += '' if message and message.endswith('\n') else '\n'
        super(CLIError, self).__init__(message)
        self.message = message
        self.details = (list(details) if (
            isinstance(details, list) or isinstance(details, tuple)) else [
                '%s' % details]) if details else []
        try:
            self.importance = int(importance or 0)
        except ValueError:
            self.importance = 0

    def __str__(self):
        return self.message


class CLIUnimplemented(CLIError):
    def __init__(
            self,
            message='I \'M SORRY, DAVE.\nI \'M AFRAID I CAN\'T DO THAT.',
            details=[
                '      _        |',
                '   _-- --_     |',
                '  --     --    |',
                ' --   .   --   |',
                ' -_       _-   |',
                '   -_   _-     |',
                '      -        |'],
            importance=3):
        super(CLIUnimplemented, self).__init__(message, details, importance)


class CLIBaseUrlError(CLIError):
    def __init__(
            self,
            message='', details=[], importance=2, service=None):
        service = '%s' % (service or '')
        message = message or 'No URL for %s' % service.lower()
        details = details or [
            'To resolve this:',
            'Set the authentication URL and TOKEN:',
            '  kamaki config set cloud.<CLOUD NAME>.url <AUTH_URL>',
            '  kamaki config set cloud.<CLOUD NAME>.token <t0k3n>',
            'OR',
            'set a service-specific URL and/or TOKEN',
            '  kamaki config set '
            'cloud.<CLOUD NAME>.%s_url <URL>' % (service or '<SERVICE>'),
            '  kamaki config set '
            'cloud.<CLOUD NAME>.%s_token <TOKEN>' % (service or '<SERVICE>')]
        super(CLIBaseUrlError, self).__init__(message, details, importance)


class CLISyntaxError(CLIError):
    def __init__(self, message='Syntax Error', details=[], importance=1):
        super(CLISyntaxError, self).__init__(message, details, importance)


class CLIInvalidArgument(CLISyntaxError):
    def __init__(self, message='Invalid Argument', details=[], importance=1):
        super(CLIInvalidArgument, self).__init__(message, details, importance)


class CLIUnknownCommand(CLIError):
    def __init__(self, message='Unknown Command', details=[], importance=1):
        super(CLIUnknownCommand, self).__init__(message, details, importance)


class CLICmdSpecError(CLIError):
    def __init__(
            self, message='Command Specification Error',
            details=[], importance=0):
        super(CLICmdSpecError, self).__init__(message, details, importance)


def raiseCLIError(err, message='', importance=0, details=[]):
    """
    :param err: (Exception) the original error message, if None, a new
        CLIError is born which is conceptually bind to raiser

    :param message: (str) a custom error message that overrides err's

    :param importance: (int) instruction to called application (e.g. for
        coloring printed error messages)

    :param details: (list) various information on the error

    :raises CLIError: it is the purpose of this method
    """
    from traceback import format_stack

    stack = ['%s' % type(err)] if err else ['<kamaki.cli.errors.CLIError>']
    stack += format_stack()

    details = list(details) if (
        isinstance(details, list) or isinstance(details, tuple)) else [
            '%s' % details]
    err_details = getattr(err, 'details', [])
    if isinstance(err_details, list) or isinstance(err_details, tuple):
        details += list(err_details)
    else:
        details.append('%s' % err_details)

    origerr = (('%s' % err) or '%s' % type(err)) if err else stack[0]
    message = '%s' % message or origerr

    try:
        status = err.status or err.errno
    except AttributeError:
        try:
            status = err.errno
        except AttributeError:
            status = None

    if origerr not in details + [message]:
        details.append(origerr)

    message += '' if message and message.endswith('\n') else '\n'
    if status:
        message = '(%s) %s' % (status, message)
        try:
            status = int(status)
        except ValueError:
            raise CLIError(message, details, importance or 0)
        importance = importance or status // 100
    importance = getattr(err, 'importance', importance)
    raise CLIError(message, details, importance)
