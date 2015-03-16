# Copyright 2015 GRNET S.A. All rights reserved.
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

from datetime import date

from kamaki.cli import command
from kamaki.cli.errors import CLIError
from kamaki.cli.cmdtree import CommandTree
from kamaki.cli.cmds import errors, OptionalOutput
from kamaki.cli.cmds.pithos import _PithosAccount
from kamaki.cli.argument import FlagArgument

scripts_cmds = CommandTree('scripts', 'Useful scripts')
namespaces = [scripts_cmds, ]


@command(scripts_cmds)
class scripts_verifyfs(_PithosAccount, OptionalOutput):
    """Verify/Fix the structure of directory objects inside a container"""

    arguments = dict(
        fix_conflicts=FlagArgument(
            'Fix conflicting names by renaming them '
            '(prepare the structure of directory objects to be consistent)',
            '--fix-conflicts'),
        fix_names=FlagArgument(
            'Rename directory objects containing \\',
            '--fix-dir-names'),
        fix_missing=FlagArgument(
            'Create missing directories objects',
            '--fix-missing-dirs'),
        yes=FlagArgument('Do not prompt for permission', '--yes'),
    )

    @errors.Generic.all
    @errors.Pithos.connection
    @errors.Pithos.container
    def _run(self):
        dirs, files, empty_files = [], [], []
        result = self.client.container_get()
        for o in result.json:
            name = o['name']
            if self.object_is_dir(o):
                dirs.append(name)
            elif o['bytes'] == 0:
                empty_files.append(name)
            else:
                files.append(name)

        # Find all directories with backslashes
        wrong = set()
        for d in dirs:
            if '\\' in d:
                wrong.add(d)

        # Find all intermediate directories and see if a missing directory
        # exists or if an intermediate directory conflicts with an existing
        # object name
        missing = set()
        conflicts = set()
        for n in files + dirs:
            inter = n.split('/')
            inter.pop()
            d = []
            for i in inter:
                d.append(i)
                p = '/'.join(d)
                if p not in dirs:
                    missing.add(p)
                if p in files + empty_files:
                    conflicts.add(p)

        # First try to resolve conflicts
        if self['fix_conflicts']:
            for c in conflicts:
                if self['yes'] or self.ask_user('Rename %s?' % c):
                    backup = '%s_orig_%s' % (c, date.today().isoformat())
                    # TODO: check if backup name already exists
                    self.error(' * Renaming %s to %s' % (c, backup))
                    self.client.move_object(
                        src_container=self.client.container,
                        src_object=c,
                        dst_container=self.client.container,
                        dst_object=backup)

        elif conflicts:
            raise CLIError(
                'Conflicting object names found: %s' % conflicts,
                details=[
                    'They should be directory objects instead',
                    'Use --fix-conflicts to rename them and prepare'
                    ' the directory structure for further fix actions'])

        # renames should take place after fixing conflicts
        elif self['fix_names']:
            for w in wrong:
                correct = w.replace('\\', '/')
                if self['yes'] or self.ask_user('Rename %s?' % w):
                    self.error(' * Renaming %s to %s' % (w, correct))
                    self.client.move_object(
                        src_container=self.client.container,
                        src_object=w,
                        dst_container=self.client.container,
                        dst_object=correct)
        elif wrong:
            raise CLIError(
                'Directory objects with backslashes found: %s' % wrong,
                details=['Use --fix-dir-names to sanitize them'])

        # missing dirs should be created after fixing names
        elif self['fix_missing']:
            for d in missing:
                if self['yes'] or self.ask_user('Create %s?' % d):
                    self.error(' * Creating directory object %s' % d)
                    self.client.create_directory(d)

        elif missing:
            raise CLIError(
                'Missing directory objects found: %s' % missing,
                details=['Use --fix-missing-dirs to create them'])

    def main(self, container):
        super(self.__class__, self)._run()
        self.container, self.client.container = container, container
        self._run()
