#!/bin/bash

set +euxo pipefail

# run worker
while true; do
	su -c "/env/bin/python spongeauth/manage.py rqworker default" spongeauth
done
