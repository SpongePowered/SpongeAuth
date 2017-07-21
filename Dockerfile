FROM debian:testing

RUN apt-get update \
  && DEBIAN_FRONTEND=noninteractive \
     apt-get -y install curl apt-transport-https gnupg2 \
  && curl -s https://deb.nodesource.com/gpgkey/nodesource.gpg.key | apt-key add - \
  && echo 'deb https://deb.nodesource.com/node_8.x stretch main' > /etc/apt/sources.list.d/nodesource.list \
  && apt-get update \
  && DEBIAN_FRONTEND=noninteractive \
     apt-get -y install \
    python2.7 \
    python3.6 \
    python3.6-dev \
    python3.6-venv \
    build-essential \
    nodejs \
    libz3-dev \
    libjpeg62-turbo-dev \
    libpng-dev \
    postgresql-client \
    libpq-dev \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/* \
  && npm install npm@latest -g

WORKDIR /app

COPY requirements /app/requirements
RUN python3.6 -m venv /env \
  && /env/bin/pip install \
    -r /app/requirements/prod.txt \
    -r /app/requirements/dev.txt

COPY package.json /app/package.json
RUN npm install \
  && npm install gulp-cli

COPY . /app

ENV DJANGO_SETTINGS_MODULE=spongeauth.settings.docker

CMD ["/app/hack/run.sh"]
