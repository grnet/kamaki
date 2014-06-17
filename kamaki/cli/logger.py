# Copyright 2013-2014 GRNET S.A. All rights reserved.
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

from os import chmod
from os.path import expanduser
from sys import stderr
import logging


LOG_FILE = [expanduser('~/.kamaki.log')]
ALL = 0

_blacklist = {}


def deactivate(name):
    """Deactivate a logger. Can be restored"""
    xlogger = logging.getLogger(name)
    _blacklist[name] = xlogger.level
    xlogger.setLevel(logging.CRITICAL)


def activate(name):
    """Restore a loggers settings"""
    old_logger = logging.getLogger(name)
    old_logger.setLevel(_blacklist.pop(name, old_logger.level))


def if_logger_enabled(func):
    def wrap(name, *args, **kwargs):
        if name in _blacklist:
            return logging.getLogger(name)
        return func(name, *args, **kwargs)
    return wrap


def get_log_filename():
    for logfile in LOG_FILE:
        try:
            with open(logfile, 'a+') as f:
                f.seek(0)
            chmod(logfile, 0600)
        except IOError as e:
            stderr.write(
                'WARNING: Failed to use file "%s" for logging\n' % logfile)
            stderr.write('\t%s\n' % e)
            stderr.flush()
            continue
        return logfile
    stderr.write('WARNING: No valid log files, redirect logs to std err\n')
    stderr.flush()


def set_log_filename(filename):
    global LOG_FILE
    LOG_FILE[0] = filename


def _add_logger(name, level=None, filename=None, fmt=None):
    log = get_logger(name)
    h = logging.FileHandler(filename) if (
        filename) else logging.StreamHandler()
    lfmt = logging.Formatter(fmt or '%(name)s\n %(message)s')
    h.setFormatter(lfmt)
    log.addHandler(h)
    log.setLevel(level or logging.DEBUG)
    return log


@if_logger_enabled
def add_file_logger(name, level=None, filename=None):
    try:
        fmt = '%(name)s(%(levelname)s) %(asctime)s\n  %(message)s' if (
            level == logging.DEBUG) else '%(name)s: %(message)s'
        return _add_logger(
            name, level, filename or get_log_filename(), fmt=fmt)
    except Exception:
        return get_logger(name)


@if_logger_enabled
def add_stream_logger(name, level=None, fmt=None):
    try:
        return _add_logger(name, level, fmt=fmt)
    except Exception:
        return get_logger(name)


@if_logger_enabled
def get_logger(name):
    return logging.getLogger(name)
