"""Migration - Base class for all database migrations."""


class Migration:
    """Base class for all database migrations. Override up() and down()."""

    def up(self):
        raise NotImplementedError

    def down(self):
        raise NotImplementedError
