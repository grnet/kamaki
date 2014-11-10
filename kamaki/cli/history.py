# Copyright 2012-2014 GRNET S.A. All rights reserved.
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
from logging import getLogger


log = getLogger(__name__)


class History(object):
    ignore_commands = ['config set', ]

    def __init__(self, filepath, token=None):
        self.filepath = filepath
        self.token = token
        self._limit = 0
        self.counter = 0

    def __getitem__(self, cmd_ids):
        with codecs.open(self.filepath, mode='r', encoding='utf-8') as f:
                lines = f.readlines()
        try:
            self.counter = int(lines[0])
            lines = lines[1:]
        except ValueError:
            # History file format is old, fix it
            self.counter = 0
            with codecs.open(self.filepath, mode='w', encoding='utf-8') as f:
                f.write('0\n%s' % ''.join(lines))
        try:
            return lines[cmd_ids]
        except IndexError:
            return None

    @property
    def limit(self):
        return self._limit

    @limit.setter
    def limit(self, new_limit):
        new_limit = int(new_limit)
        if new_limit < 0:
            raise ValueError('Invalid history limit (%s)' % new_limit)
        old_limit, self._limit = self._limit, new_limit
        if self._limit and ((not old_limit) or (self._limit <= old_limit)):
            with codecs.open(self.filepath, mode='r', encoding='utf-8') as f:
                lines = f.readlines()
                self.counter = int(lines[0])
                old_len = len(lines[1:])
            if old_len > new_limit:
                self.counter += old_len - new_limit
                with codecs.open(
                        self.filepath, mode='w', encoding='utf-8') as f:
                    f.write('%s\n' % self.counter)
                    f.write(''.join(lines[old_len - new_limit + 1:]))
                    f.flush()

    @classmethod
    def _match(self, line, match_terms):
        if match_terms:
            return all(term in line for term in match_terms.split())
        return True

    def get(self, match_terms=None, limit=0):
        """DEPRECATED since 0.14"""
        limit = int(limit or 0)
        r = ['%s.\t%s' % (i + 1, line) for i, line in enumerate(self[:]) if (
                self._match(line, match_terms))]
        return r[- limit:]

    def add(self, line):
        line = '%s' % line or ''
        bline = [w.lower() for w in line.split() if not w.startswith('-')]
        for cmd in self.ignore_commands:
            cmds = [w.lower() for w in cmd.split()]
            if cmds == bline[1:len(cmds) + 1]:
                log.debug('History ignored a command of type "%s"' % cmd)
                return
        line = line.replace(self.token, '...') if self.token else line
        try:
            with codecs.open(self.filepath, mode='a+', encoding='utf-8') as f:
                f.write(line + '\n')
                f.flush()
            self.limit = self.limit
        except Exception as e:
            log.debug('Add history failed for "%s" (%s)' % (line, e))

    def empty(self):
        with open(self.filepath, 'w') as f:
            f.write('0\n')
            f.flush()
        self.counter = 0

    def clean(self):
        """DEPRECATED since version 0.14"""
        return self.empty()

    def retrieve(self, cmd_id):
        if not cmd_id:
            return None
        cmd_id = int(cmd_id)
        return self[cmd_id - (1 if cmd_id > 0 else 0)]
