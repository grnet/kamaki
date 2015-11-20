#!/usr/bin/env sh

set -e

python kamaki/cli/test.py
python kamaki/clients/test.py
