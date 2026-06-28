"""
Laraflask Observer
[ID] Base class untuk Model Observer — pola untuk memisahkan logic
lifecycle (creating/created/updating/updated/dst) dari Model itu sendiri.
Didaftarkan lewat `Model.observe(ObserverClass)`.

CATATAN PENTING: lifecycle event Model (`ModelCreating`, `ModelCreated`,
dkk di `laraflask.events.dispatcher`) saat ini BELUM di-dispatch otomatis
dari `Model.save()`/`delete()`. Observer yang didaftarkan lewat
`Model.observe()` di bawah ini TERPANGGIL saat event yang sesuai
di-dispatch secara manual (lihat contoh), bukan otomatis pada setiap
save()/delete(). Lihat README bagian "Known Limitations".

[EN] Base class for Model Observers — a pattern for separating lifecycle
logic (creating/created/updating/updated/etc.) from the Model itself.
Registered via `Model.observe(ObserverClass)`.

IMPORTANT NOTE: Model lifecycle events (`ModelCreating`, `ModelCreated`,
etc. in `laraflask.events.dispatcher`) are currently NOT automatically
dispatched from `Model.save()`/`delete()`. Observers registered via
`Model.observe()` below are invoked when the matching event is dispatched
manually (see the example), not automatically on every save()/delete().
See the "Known Limitations" section of the README.
"""

from __future__ import annotations
from typing import Any


class Observer:
    """
    [ID] Class dasar Observer. Override hanya hook yang dibutuhkan; sisanya
    default no-op. Contoh:

        class UserObserver(Observer):
            def created(self, user):
                send_welcome_email(user)

        User.observe(UserObserver)

        # Karena lifecycle event belum otomatis, dispatch manual untuk saat ini:
        user = User(name='Rio', email='rio@example.com')
        Events.dispatch(ModelCreating(user))
        user.save()
        Events.dispatch(ModelCreated(user))

    [EN] Base Observer class. Override only the hooks you need; the rest
    default to no-ops. Example above.
    """

    def creating(self, model: Any) -> None:
        pass

    def created(self, model: Any) -> None:
        pass

    def updating(self, model: Any) -> None:
        pass

    def updated(self, model: Any) -> None:
        pass

    def deleting(self, model: Any) -> None:
        pass

    def deleted(self, model: Any) -> None:
        pass

    def saving(self, model: Any) -> None:
        pass

    def saved(self, model: Any) -> None:
        pass

    def restoring(self, model: Any) -> None:
        pass

    def restored(self, model: Any) -> None:
        pass
