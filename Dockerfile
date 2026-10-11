# syntax=docker/dockerfile:1

#########################################
#                ASSETS                 #
#########################################

FROM node:22-alpine3.24 AS assets

WORKDIR /app

COPY package.json package-lock.json gulpfile.mjs ./
RUN npm ci

COPY spongeauth/static spongeauth/static
RUN npx gulp build

#########################################
#             PYTHON DEPS               #
#########################################

FROM python:3.12-alpine3.24 AS builder

# git: django-user-sessions is installed from a pinned git commit
RUN apk add --no-cache git

COPY requirements /requirements
# Install the git dependency as a regular (non-editable) package so the venv can be copied as-is
RUN sed -i 's/^-e //' /requirements/base.txt \
    && python -m venv /home/spongeauth/env \
    && /home/spongeauth/env/bin/pip install --no-cache-dir -r /requirements/prod.txt

#########################################
#                 FINAL                 #
#########################################

FROM python:3.12-alpine3.24

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_NAME=spongeauth \
    HOME=/home/spongeauth \
    APP_HOME=/home/spongeauth/app \
    DJANGO_SETTINGS_MODULE=spongeauth.settings.prod

RUN addgroup -g 1000 -S $APP_NAME && adduser -u 1000 -S $APP_NAME -G $APP_NAME \
    && mkdir -p $HOME/public_html/static $HOME/public_html/media \
    && chown -R $APP_NAME:$APP_NAME $HOME

WORKDIR $APP_HOME

COPY --from=builder /home/spongeauth/env $HOME/env
COPY --chown=$APP_NAME:$APP_NAME . $APP_HOME
COPY --from=assets --chown=$APP_NAME:$APP_NAME /app/spongeauth/static-build $APP_HOME/spongeauth/static-build

USER $APP_NAME

EXPOSE 8080

ENTRYPOINT ["sh", "-c", "$APP_HOME/entrypoint/run.sh"]
