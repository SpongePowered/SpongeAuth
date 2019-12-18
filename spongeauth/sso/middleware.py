import django.contrib.sessions.middleware
import user_sessions.middleware


class UserSessionsMiddleware(
        user_sessions.middleware.SessionMiddleware,
        django.contrib.sessions.middleware.SessionMiddleware):
    pass
