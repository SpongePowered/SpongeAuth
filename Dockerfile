#########################################
#                BUILDER                #
#########################################

FROM python:3-alpine as builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN apk update \
    && apk add postgresql-dev python3-dev nodejs npm git py-pip zlib-dev jpeg-dev libpng-dev libwebp-dev musl-dev gcc py3-virtualenv

COPY . /app

RUN python3 -m venv /venv && /venv/bin/pip install --upgrade --no-cache pip wheel && \
    /venv/bin/pip wheel --no-cache-dir --wheel-dir /app/wheels \
    -r /app/requirements/base.txt \
    -r /app/requirements/prod.txt

RUN npm ci
RUN production=true node_modules/.bin/gulp build

#########################################
#                 FINAL                 #
#########################################

FROM python:3-alpine

ENV APP_NAME=spongeauth
ENV HOME=/home/$APP_NAME
ENV APP_HOME=$HOME/app

RUN mkdir -p $APP_HOME
RUN addgroup -g 1000 -S $APP_NAME && adduser -u 1000 -S $APP_NAME -G $APP_NAME
WORKDIR $APP_HOME

RUN apk update && apk add libpq py3-virtualenv zlib-dev jpeg-dev libpng-dev libwebp-dev

COPY . $APP_HOME
COPY --from=builder /app/spongeauth/static-build $APP_HOME/spongeauth/static-build
COPY --from=builder /app/wheels /wheels
RUN mkdir -p $HOME/public_html/static
RUN mkdir -p $HOME/public_html/media

RUN chown -R $APP_NAME:$APP_NAME $HOME
USER $APP_NAME

RUN sed -i 's/-e\ git+https:\/\/github\.com\/felixoi\/django-user-sessions.git#egg=//g' $APP_HOME/requirements/base.txt
RUN python3 -m venv $HOME/env && $HOME/env/bin/pip install --upgrade --no-cache pip && $HOME/env/bin/pip install \
    -r requirements/base.txt \
    -r requirements/prod.txt \
    --no-cache /wheels/*

ENV DJANGO_SETTINGS_MODULE=spongeauth.settings.prod

ENTRYPOINT ["sh", "-c", "$APP_HOME/entrypoint/run.sh"]
