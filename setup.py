#!/usr/bin/env python

# Copyright 2011-2015 GRNET S.A. All rights reserved.
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

from setuptools import setup
from sys import version_info

import kamaki


optional = ['ansicolors', 'mock>=1.0.1']

requires = ['objpool>=0.2', 'progress>=1.1', 'astakosclient>=0.14.10', 'python-dateutil']

if version_info < (2, 7):
    requires.append('argparse')

setup(
    name='kamaki',
    version=kamaki.__version__,
    description=('A multipurpose, interactive command-line tool, and also a'
                 ' client development library for managing OpenStack clouds.'),
    long_description=open('README.md').read(),
    url='http://www.synnefo.org',
    download_url='https://pypi.python.org/pypi/kamaki',
    license='BSD',
    author='Synnefo development team',
    author_email='synnefo-devel@googlegroups.com',
    maintainer='Synnefo development team',
    maintainer_email='synnefo-devel@googlegroups.com',
    packages=[
        'kamaki',
        'kamaki.cli',
        'kamaki.cli.utils',
        'kamaki.cli.config',
        'kamaki.cli.argument',
        'kamaki.cli.cmds',
        'kamaki.cli.cmdtree',
        'kamaki.cli.contrib',
        'kamaki.clients',
        'kamaki.clients.utils',
        'kamaki.clients.astakos',
        'kamaki.clients.image',
        'kamaki.clients.storage',
        'kamaki.clients.pithos',
        'kamaki.clients.compute',
        'kamaki.clients.network',
        'kamaki.clients.cyclades',
        'kamaki.clients.blockstorage',
    ],
    classifiers=[
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'Environment :: Console',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Topic :: System :: Shells',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Utilities'
        ],
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'kamaki = kamaki.cli:run_one_cmd',
            'kamaki-shell = kamaki.cli:run_shell'
        ]
    },
    install_requires=requires
)
