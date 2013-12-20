#!/usr/bin/env python

# Copyright 2012-2013 GRNET S.A. All rights reserved.
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

import codecs


class History(object):
    def __init__(self, filepath, token=None):
        self.filepath = filepath
        self.token = token

    @classmethod
    def _match(self, line, match_terms):
        if match_terms is None:
            return True
        for term in match_terms.split():
            if term not in line:
                return False
        return True

    def get(self, match_terms=None, limit=0):
        limit = int(limit or 0)
        with codecs.open(self.filepath, mode='r', encoding='utf-8') as f:
            result = [u'%s.  \t%s' % (
                i + 1, line) for i, line in enumerate(f.readlines())
                if self._match(line, match_terms)]
            return result[- limit:]

    def add(self, line):
        line = line.replace(self.token, '...') if self.token else line
        with open(self.filepath, 'a+') as f:
            f.write(line + '\n')

    def clean(self):
        with open(self.filepath, 'w'):
            pass

    def retrieve(self, cmd_id):
        """
        :param cmd_id: (int) the id of the command to retrieve can be positive
            or negative, zero values are ignored

        :returns: (str) the stored command record without the id
        """
        cmd_id = int(cmd_id)
        if not cmd_id:
            return None
        with open(self.filepath) as f:
            try:
                cmd_list = f.readlines()[:-1]  # exclude current command
                return cmd_list[cmd_id - (1 if cmd_id > 0 else 0)]
            except IndexError:
                return None
