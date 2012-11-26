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

from json import loads


class CLIError(Exception):
    def __init__(self, message, details=[], importance=0):
        """
        @message is the main message of the Error
        @detauls is a list of previous errors
        @importance of the output for the user
            Suggested values: 0, 1, 2, 3
        """
        super(CLIError, self).__init__(message)
        self.details = details if isinstance(details, list)\
            else [] if details is None else ['%s' % details]
        try:
            self.importance = int(importance)
        except ValueError:
            self.importance = 0


class CLISyntaxError(CLIError):
    def __init__(self, message='Syntax Error', details=[], importance=1):
        super(CLISyntaxError, self).__init__(message, details, importance)


class CLIUnknownCommand(CLIError):
    def __init__(self, message='Unknown Command', details=[], importance=1):
        super(CLIUnknownCommand, self).__init__(message, details, importance)


class CLICmdSpecError(CLIError):
    def __init__(self,
        message='Command Specification Error', details=[], importance=0):
        super(CLICmdSpecError, self).__init__(message, details, importance)


class CLICmdIncompleteError(CLICmdSpecError):
    def __init__(self,
        message='Incomplete Command Error', details=[], importance=1):
        super(CLICmdSpecError, self).__init__(message, details, importance)


def raiseCLIError(err, importance=0):
    message = '%s' % err
    if err.status:
        message = '(%s) %s' % (err.status, err)
        try:
            status = int(err.status)
        except ValueError:
            raise CLIError(message, err.details, importance)
        importance = status // 100
    raise CLIError(message, err.details, importance)
