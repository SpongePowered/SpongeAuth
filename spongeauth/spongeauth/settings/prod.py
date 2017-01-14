import os
import os.path
import raven

from .base import *

DEBUG = False
GIT_REPO_ROOT = os.path.dirname(BASE_DIR)
PARENT_ROOT = os.path.dirname(GIT_REPO_ROOT)

TEMPLATES = [
    {   
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            os.path.join(BASE_DIR, 'templates'),
        ],
        'OPTIONS': {
            'loaders': [
                ('django.template.loaders.cached.Loader', [
                    'django.template.loaders.filesystem.Loader',
                    'django.template.loaders.app_directories.Loader',
                ]),
            ],
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

INSTALLED_APPS += [
    'raven.contrib.django.raven_compat',
]

DISCOURSE_SSO_SECRET = os.environ['DISCOURSE_SSO_SECRET']

RAVEN_CONFIG = {
    'dsn': os.environ['RAVEN_DSN'],
    'release': raven.fetch_git_sha(GIT_REPO_ROOT),
}

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'spongeauth',
        'HOST': '',
        'ATOMIC_REQUESTS': True,
    }
}

STATICFILES_STORAGE = 'django.contrib.staticfiles.storage.ManifestStaticFilesStorage'
STATIC_ROOT = os.path.join(PARENT_ROOT, 'public_html', 'static')
MEDIA_ROOT = os.path.join(PARENT_ROOT, 'public_html', 'media')


if not os.environ.get('DJANGO_SETTINGS_SKIP_LOCAL', False):
    try:
        from .local_settings import *
    except ImportError:
        pass
