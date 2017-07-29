from .dev import *

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'spongeauth',
        'USER': 'spongeauth',
        'PASSWORD': 'spongeauth',
        'HOST': 'db',
        'ATOMIC_REQUESTS': True,
    }
}

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_USE_TLS = False
EMAIL_USE_SSL = False
EMAIL_HOST = 'mail'
EMAIL_PORT = 1025
REQUIRE_EMAIL_CONFIRM = True

DEBUG_TOOLBAR_CONFIG = {
    'SHOW_TOOLBAR_CALLBACK': __name__ + '.show_toolbar',
}
def show_toolbar(request):
    return DEBUG
