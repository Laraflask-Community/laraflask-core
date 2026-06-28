"""
Laraflask Seeder
[ID] Base class untuk database seeder — dipakai untuk mengisi data awal
(dummy/sample data) ke database lewat `python artisan.py db:seed`.
Subclass cukup mengimplementasikan `run()`.

[EN] Base class for database seeders — used to populate the database with
initial/dummy/sample data via `python artisan.py db:seed`. Subclasses
only need to implement `run()`.
"""

from __future__ import annotations
from typing import Any, List, Type


class Seeder:
    """
    [ID] Class dasar seeder. Contoh:

        class UserSeeder(Seeder):
            def run(self):
                User.create(name='Admin', email='admin@example.com', password='secret')

    [EN] Base seeder class. Example above.
    """

    def run(self) -> None:
        """
        [ID] Override method ini dengan logic seeding sesungguhnya.
        [EN] Override this method with the actual seeding logic.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement run()."
        )

    def call(self, *seeder_classes: Type['Seeder']) -> None:
        """
        [ID] Jalankan satu atau beberapa seeder lain dari dalam seeder ini
        — berguna untuk `DatabaseSeeder` utama yang memanggil beberapa
        seeder spesifik secara berurutan.

        [EN] Run one or more other seeders from within this seeder —
        useful for a main `DatabaseSeeder` that calls several specific
        seeders in sequence.
        """
        for seeder_class in seeder_classes:
            seeder_class().run()
