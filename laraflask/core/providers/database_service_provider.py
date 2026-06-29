"""DatabaseServiceProvider."""

from laraflask.core.providers.service_provider import ServiceProvider


class DatabaseServiceProvider(ServiceProvider):
    """Register database services."""

    def register(self):
        self.app.singleton('db', self._make_db)

    def boot(self):
        db = self.app.make('db')
        db_url = self.app._flask.config.get('SQLALCHEMY_DATABASE_URI')
        if db_url:
            try:
                db.connect(url=db_url)
            except Exception as e:
                import logging
                logging.getLogger('laraflask').warning(f"DB connect failed: {e}")

    def _make_db(self, app):
        from laraflask.orm.db import DB
        return DB
