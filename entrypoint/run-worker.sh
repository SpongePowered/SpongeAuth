#!/bin/sh

set +euxo pipefail

# run worker
$HOME/env/bin/python spongeauth/manage.py rqworker default
