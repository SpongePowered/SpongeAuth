from user_sessions.backends import db


class SessionStore(db.SessionStore):
    """user_sessions' store with a guard for session cookies that have no row.

    Django's _get_session_from_db returns None for an unknown or expired
    session key (load() then starts an empty session), but user_sessions
    reads s.user_id unconditionally, so a stale cookie raised AttributeError
    and every page 500ed until the cookie was cleared. Unfixed upstream as
    of django-user-sessions 3.0.3.
    """

    def _get_session_from_db(self):
        # Django's lookup, skipping user_sessions' unguarded override.
        s = super(db.SessionStore, self)._get_session_from_db()
        if s is not None:
            self.user_id = s.user_id
            # do not overwrite user_agent/ip, as those might have been updated
            if self.user_agent != s.user_agent or self.ip != s.ip:
                self.modified = True
        return s
