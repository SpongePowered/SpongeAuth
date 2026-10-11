#!/bin/sh

set -euxo pipefail

cd $APP_HOME

# set RUN_MIGRATIONS=false when migrations run elsewhere (init container / Job)
if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
    $HOME/env/bin/python spongeauth/manage.py migrate --noinput
fi
$HOME/env/bin/python spongeauth/manage.py collectstatic --noinput

set +euxo pipefail

# run worker - necessary for background sso syncs
./entrypoint/run-worker.sh &

exec $HOME/env/bin/gunicorn -b :8080 -w 4 --no-control-socket --chdir spongeauth spongeauth.wsgi
