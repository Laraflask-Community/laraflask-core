"""SessionServiceProvider."""

from laraflask.core.providers.service_provider import ServiceProvider


class SessionServiceProvider(ServiceProvider):
    """Register session services."""

    def register(self):
        pass

    def boot(self):
        import os
        flask_app = self.app._flask
        flask_app.config['SESSION_TYPE'] = os.getenv('SESSION_DRIVER', 'filesystem')
        flask_app.config['SESSION_FILE_DIR'] = os.path.join(
            self.app.storage_path(), 'framework', 'sessions'
        )
        flask_app.config['SESSION_PERMANENT'] = False
        flask_app.config['SESSION_USE_SIGNER'] = True
        flask_app.config['PERMANENT_SESSION_LIFETIME'] = int(
            os.getenv('SESSION_LIFETIME', 120)
        ) * 60

        try:
            from flask_session import Session
            Session(flask_app)
        except ImportError:
            pass  # Flask-Session optional; fall back to cookie sessions
