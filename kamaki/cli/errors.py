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
from . import CLIError

class CLIError(Exception):
    def __init__(self, message, status=0, details='', importance=0):
        """importance is set by the raiser
        0 is the lowest possible importance
        Suggested values: 0, 1, 2, 3
        """
        super(CLIError, self).__init__(message, status, details)
        self.message = message
        self.status = status
        self.details = details
        self.importance = importance

    def __unicode__(self):
        return unicode(self.message)

class CLISyntaxError(CLIError):
	def __init__(self, message, status=0, details=''):
		super(CLISyntaxError, self).__init__(message, status, details, importance=1)

class CLIUnknownCommand(CLIError):
	def __init__(self, message, status=0, details=''):
		super(CLIUnknownCommand, self).__init__(message, status, details, importance=0)

class CLICmdSpecLoadError(CLIError):
	def __init__(self, message, status=0, details=''):
		super(CLICmdSpecLoadError, self).__init__(message, status, details, importance=0)

def raiseCLIError(err, importance = -1):
    if importance < 0:
        if err.status <= 0:
            importance = 0
        elif err.status <= 400:
            importance = 1
        elif err.status <= 500:
            importance = 2
        else:
            importance = 3
    raise CLIError(err.message, err.status, err.details, importance)