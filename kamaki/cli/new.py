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
# or implied, of GRNET S.A.command

from sys import argv
from os.path import basename
from kamaki.cli.argument import _arguments, parse_known_args, init_parser

_help = False
_debug = False
_verbose = False
_colors = False


def _init_session(arguments):
    global _help
    _help = arguments['help'].value
    global _debug
    _debug = arguments['debug'].value
    global _verbose
    _verbose = arguments['verbose'].value
    global _colors
    _colors = arguments['config'].get('global', 'colors')


def one_cmd():
    print('ONE COMMAND')


def interactive_shell():
    print('INTERACTIVE SHELL')


def main():
    exe = basename(argv[0])
    parser = init_parser(exe, _arguments)
    parsed, unparsed = parse_known_args(parser, _arguments)

    if _arguments['version'].value:
        exit(0)

    _init_session(_arguments)

    if unparsed:
        one_cmd()
    elif _help:
        parser.print_help()
    else:
        interactive_shell()
