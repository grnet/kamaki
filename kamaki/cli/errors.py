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
        @message is the main message of the Error
        @defaults is a list of previous errors
        @importance of the output for the user
            Suggested values: 0, 1, 2, 3
        """
        message += '' if message and message[-1] == '\n' else '\n'
        super(CLIError, self).__init__(message)
        self.details = list(details) if isinstance(details, list)\
            else [] if details is None else ['%s' % details]
        try:
            self.importance = int(importance)
        except ValueError:
            self.importance = 0


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
    def __init__(self, message='', details=[], importance=2, service=None):
        message = message or 'No URL for %s' % service.lower()
        details = details or [
            'Two options to resolve this:',
            '(Use the correct cloud name, instead of "default")',
            'A. (recommended) Let kamaki discover the endpoint URLs for all',

            'services by setting a single Authentication URL and token:',
            '  /config set cloud.default.url <AUTH_URL>',
            '  /config set cloud.default.token <t0k3n>',
            'B. (advanced users) Explicitly set a valid %s endpoint URL' % (
                service.upper()),
            'Note: URL option has a higher priority, so delete it to',
            'make that work',
            '  /config delete cloud.default.url',
            '  /config set cloud.%s.url <%s_URL>' % (
                service, service.upper())]
        super(CLIBaseUrlError, self).__init__(message, details, importance)


class CLISyntaxError(CLIError):
    def __init__(self, message='Syntax Error', details=[], importance=1):
        super(CLISyntaxError, self).__init__(message, details, importance)


class CLIUnknownCommand(CLIError):
    def __init__(self, message='Unknown Command', details=[], importance=1):
        super(CLIUnknownCommand, self).__init__(message, details, importance)


class CLICmdSpecError(CLIError):
    def __init__(
            self, message='Command Specification Error',
            details=[], importance=0):
        super(CLICmdSpecError, self).__init__(message, details, importance)


class CLICmdIncompleteError(CLICmdSpecError):
    def __init__(
            self, message='Incomplete Command Error',
            details=[], importance=1):
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
    try:
        stack = [e for e in stack if e != stack[1]]
    except KeyError:
        log.debug('\n   < '.join(stack))

    details = ['%s' % details] if not isinstance(details, list)\
        else list(details)
    details += getattr(err, 'details', [])

    if err:
        origerr = '%s' % err
        origerr = origerr if origerr else '%s' % type(err)
    else:
        origerr = stack[0]

    message = '%s' % (message if message else origerr)

    try:
        status = err.status or err.errno
    except AttributeError:
        status = None

    if origerr not in details + [message]:
        details.append(origerr)

    message += '' if message and message[-1] == '\n' else '\n'
    if status:
        message = '(%s) %s' % (err.status, message)
        try:
            status = int(err.status)
        except ValueError:
            raise CLIError(message, details, importance)
        importance = importance if importance else status // 100
    importance = getattr(err, 'importance', importance)
    raise CLIError(message, details, importance)
