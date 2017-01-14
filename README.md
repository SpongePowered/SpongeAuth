SpongeAuth
==========

[![Build Status](https://travis-ci.org/lukegb/SpongeAuth.svg?branch=master)](https://travis-ci.org/lukegb/SpongeAuth) [![Coverage Status](https://coveralls.io/repos/github/lukegb/SpongeAuth/badge.svg?branch=master)](https://coveralls.io/github/lukegb/SpongeAuth?branch=master)

An authentication portal for shared user accounts between Sponge services.

Originally written in Play, but ported to Django and made more robust with more extensive testing.

Developing
----------

You'll need:

* Python 3.6 or above
* A recent version of Node.js and NPM

To install all the dependencies, from the root of your fresh checkout, run:

```
python3 -m venv env
source env/bin/activate
pip install -r requirements/dev.txt
npm install
npm install gulp-cli
node_modules/.bin/gulp build
```

Then, to bootstrap the database:

```
python spongeauth/manage.py migrate
```

You can then start the webserver on localhost:8000 by running:

```
python spongeauth/manage.py runserver
```

If you're working on the CSS, JavaScript, or other frontend stuff, you should also run gulp in the background to watch when you make changes and push them into the correct place for Django to pick them up:

```
node_modules/.bin/gulp
```
