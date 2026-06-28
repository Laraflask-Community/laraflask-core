"""
Laraflask Factory
[ID] Base class untuk model factory — menghasilkan instance/data dummy
untuk testing atau seeding, terhubung ke `Faker` (lib `faker`, lihat
extras `testing`). Subclass cukup men-set atribut `model` dan
mengimplementasikan `definition()`.

[EN] Base class for model factories — produces dummy instances/data for
testing or seeding, wired to `Faker` (the `faker` package, see the
`testing` extras). Subclasses only need to set the `model` attribute and
implement `definition()`.
"""

from __future__ import annotations
from typing import Any, Dict, List, Optional, Type


class Factory:
    """
    [ID] Class dasar factory. Contoh:

        class UserFactory(Factory):
            model = User

            def definition(self) -> dict:
                return {
                    'name': self.faker.name(),
                    'email': self.faker.unique().email(),
                }

        user = UserFactory().create()                 # simpan ke DB
        user = UserFactory().make()                     # instance saja, tidak disimpan
        users = UserFactory().count(10).create()        # buat 10 sekaligus

    [EN] Base factory class. Example above.
    """

    model: Optional[Type[Any]] = None

    def __init__(self):
        self._count = 1
        self._overrides: Dict[str, Any] = {}
        self._faker = None

    @property
    def faker(self):
        """
        [ID] Instance `Faker` siap pakai. Lempar error yang jelas jika
        package `faker` belum terinstal, alih-alih `ImportError` mentah.

        [EN] A ready-to-use `Faker` instance. Raises a clear error if the
        `faker` package isn't installed, instead of a bare `ImportError`.
        """
        if self._faker is None:
            try:
                from faker import Faker
            except ImportError:
                raise ImportError(
                    "Factory.faker requires the 'faker' package. "
                    "Install it with: pip install laraflask-core[testing]"
                )
            self._faker = Faker()
        return self._faker

    def definition(self) -> Dict[str, Any]:
        """
        [ID] Override dengan default attributes untuk model ini.
        [EN] Override with the default attributes for this model.
        """
        return {}

    def state(self, **overrides) -> 'Factory':
        """
        [ID] Timpa sebagian attribute dari `definition()` default — bisa
        di-chain. Contoh: `UserFactory().state(is_admin=True).create()`.

        [EN] Override some attributes from the default `definition()` —
        chainable. Example: `UserFactory().state(is_admin=True).create()`.
        """
        self._overrides.update(overrides)
        return self

    def count(self, n: int) -> 'Factory':
        """[ID] Set jumlah instance yang dibuat oleh create()/make(). [EN] Set how many instances create()/make() will produce."""
        self._count = n
        return self

    def make(self) -> Any:
        """
        [ID] Buat instance model TANPA menyimpan ke database. Jika
        `count()` > 1, return list instance.

        [EN] Build a model instance WITHOUT persisting it to the database.
        If `count()` > 1, returns a list of instances.
        """
        if self.model is None:
            raise NotImplementedError(
                f"{self.__class__.__name__} must set the 'model' attribute."
            )

        instances = [self._build_one() for _ in range(self._count)]
        return instances if self._count > 1 else instances[0]

    def create(self) -> Any:
        """
        [ID] Buat instance model DAN simpan ke database. Jika `count()` > 1,
        return list instance yang sudah tersimpan.

        [EN] Build a model instance AND persist it to the database. If
        `count()` > 1, returns a list of saved instances.
        """
        result = self.make()
        instances = result if isinstance(result, list) else [result]
        for instance in instances:
            instance.save()
        return result

    def _build_one(self) -> Any:
        attributes = {**self.definition(), **self._overrides}
        return self.model(**attributes)
