FROM debian:testing

RUN apt-get update \
  && DEBIAN_FRONTEND=noninteractive \
     apt-get -y install \
    python2.7 \
    python3 \
    python3-dev \
    python3-venv \
    build-essential \
    nodejs \
    npm \
    libz3-dev \
    libjpeg62-turbo-dev \
    libpng-dev \
    postgresql-client \
    libpq-dev \
    git \
    nano \
    tree \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/* \
  && npm install npm@latest -g

WORKDIR /app

COPY requirements /app/requirements
RUN python3 -m venv /env \
  && /env/bin/pip install \
    -r /app/requirements/prod.txt \
    -r /app/requirements/dev.txt

COPY package.json /app/package.json
RUN npm install \
  && npm install gulp-cli

COPY . /app

RUN node_modules/.bin/gulp build \
    && chmod 777 /app/entrypoint/run.sh

ENV DJANGO_SETTINGS_MODULE=spongeauth.settings.dev

CMD ["/app/entrypoint/run.sh"]
