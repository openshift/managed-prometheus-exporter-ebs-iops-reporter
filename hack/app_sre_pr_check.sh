#!/bin/bash

set -exv

python3 -m venv .venv
source .venv/bin/activate

pip install tox
tox

deactivate

# script needs to pass for app-sre workflow 
exit 0
