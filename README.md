SpongeAuth
==========

[![Build Status](https://travis-ci.org/SpongePowered/SpongeAuth.svg?branch=master)](https://travis-ci.org/SpongePowered/SpongeAuth) [![Coverage Status](https://coveralls.io/repos/github/SpongePowered/SpongeAuth/badge.svg?branch=master)](https://coveralls.io/github/SpongePowered/SpongeAuth?branch=master)

An authentication portal for shared user accounts between Sponge services.

Originally written in Play, but ported to Django and made more robust with more extensive testing.

Developing
----------

You'll need:

* A working Docker install (for Linux, install from your package manager; for macOS, use [Docker for Mac](https://docs.docker.com/docker-for-mac/install/); for Windows, use [Docker for Windows](https://docs.docker.com/docker-for-windows/install/))
* docker-compose (for Linux, install from your package manager; for macOS/Windows, these should be included with Docker for Mac/Windows)

Run

```
docker-compose up
```

and wait for a bit. When you see

```
su -c '/env/bin/python spongeauth/manage.py runserver 0.0.0.0:8000' spongeauth
```

then you should be able to visit http://localhost:8000 and have a working SpongeAuth install.

If you need an administrator account, you should be able to run:

```
docker-compose run app /env/bin/python spongeauth/manage.py createsuperuser
```

and follow the prompts to get an administrator account. This must be done after the `up` command above.
