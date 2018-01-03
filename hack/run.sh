#!/bin/bash

set -euxo pipefail

cd /app

groupadd -g "$(stat -c '%g' /app)" -o spongeauth || true
useradd -u "$(stat -c '%u' /app)" -g spongeauth -o -m spongeauth || true

# bootstrap node_modules, in case user has this directory mounted as a volume
su -c "PYTHON=python2.7 npm install" spongeauth
su -c "PYTHON=python2.7 npm install gulp-cli" spongeauth

# setup compiled scripts/fonts/etc.
su -c "node_modules/.bin/gulp build" spongeauth

# wait for database to be ready
touch ~/.pgpass
chmod 0600 ~/.pgpass
echo "db:5432:spongeauth:spongeauth:spongeauth" > ~/.pgpass
until psql -w -h 'db' -U spongeauth spongeauth -c '\l'; do
  echo "Postgres isn't ready yet..." >&2
  sleep 1
done
echo "Postgres ready, continuing" >&2

# migrate database
su -c "/env/bin/python spongeauth/manage.py migrate" spongeauth

set +euxo pipefail
(
	trap 'kill -TERM $PYTHONPID' TERM INT
	while true; do
		su -c "/env/bin/python spongeauth/manage.py runserver 0.0.0.0:8000" spongeauth &
		PYTHONPID=$!
		wait $PYTHONPID
	done
) &

(
	trap 'kill -TERM $GULPPID' TERM INT
	while true; do
		su -c "node_modules/.bin/gulp" spongeauth &
		GULPPID=$!
		wait $GULPPID
	done
) &

trap 'kill $(jobs -p)' TERM INT
wait $(jobs -p)
