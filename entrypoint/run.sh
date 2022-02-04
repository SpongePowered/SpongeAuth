#!/bin/sh

set -euxo pipefail

cd $APP_HOME

$HOME/env/bin/python spongeauth/manage.py migrate
$HOME/env/bin/python spongeauth/manage.py collectstatic --noinput

set +euxo pipefail

# run worker - necessary for background sso syncs
./entrypoint/run-worker.sh &

$HOME/env/bin/gunicorn -b :8080 -w 4 --chdir spongeauth spongeauth.wsgi
