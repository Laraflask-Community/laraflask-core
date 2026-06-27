"""
Laraflask Macroable
[ID] Mixin yang memungkinkan class manapun menerima method baru secara
dinamis saat runtime, terinspirasi dari trait Illuminate\\Support\\Traits\\Macroable
milik Laravel. Cocok untuk extension point seperti `QueryBuilder.macro(...)`.

[EN] A mixin that lets any class receive new methods dynamically at runtime,
inspired by Laravel's Illuminate\\Support\\Traits\\Macroable trait. Useful as
an extension point such as `QueryBuilder.macro(...)`.
"""

from __future__ import annotations
from typing import Any, Callable, Dict


class Macroable:
    """
    [ID] Inherit class ini agar bisa menerima method tambahan secara dinamis
    lewat `macro()` (per-class) atau `mixin()` (banyak method sekaligus).
    Macro terdaftar per subclass — mendaftarkan macro di `QueryBuilder` tidak
    akan bocor ke subclass lain yang juga mewarisi `Macroable`.

    [EN] Inherit this class to allow it to receive additional methods
    dynamically via `macro()` (one at a time) or `mixin()` (many at once).
    Macros are registered per subclass — registering a macro on
    `QueryBuilder` will not leak into unrelated subclasses that also
    inherit `Macroable`.
    """

    @classmethod
    def macro(cls, name: str, callback: Callable) -> None:
        """
        [ID] Daftarkan method baru bernama `name` ke class ini. Callback
        menerima `self` sebagai argumen pertama, sama seperti method biasa.
        Contoh: `QueryBuilder.macro('whereActive', lambda self: self.where('active', True))`.

        [EN] Register a new method named `name` on this class. The callback
        receives `self` as its first argument, just like a regular method.
        Example: `QueryBuilder.macro('whereActive', lambda self: self.where('active', True))`.
        """
        macros = cls._get_own_macros()
        macros[name] = callback
        setattr(cls, name, cls._make_macro_method(name))

    @classmethod
    def mixin(cls, mixin_obj: Any, replace: bool = True) -> None:
        """
        [ID] Daftarkan semua method publik dari sebuah object/class sebagai
        macro sekaligus. Berguna untuk menambahkan satu set fungsionalitas
        terkait ke dalam class target.

        [EN] Register every public method from an object/class as macros in
        one go. Useful for bulk-adding a related set of functionality to the
        target class.
        """
        source = mixin_obj if isinstance(mixin_obj, type) else type(mixin_obj)

        for attr_name in dir(source):
            if attr_name.startswith('_'):
                continue

            if not replace and cls.has_macro(attr_name):
                continue

            attr = getattr(source, attr_name)
            if callable(attr):
                # Unwrap bound/unbound functions to a plain callable(self, ...) form.
                func = attr.__func__ if hasattr(attr, '__func__') else attr
                cls.macro(attr_name, func)

    @classmethod
    def has_macro(cls, name: str) -> bool:
        """Determine if a macro with the given name has been registered on this class."""
        return name in cls._get_own_macros()

    @classmethod
    def flush_macros(cls) -> None:
        """
        [ID] Hapus semua macro yang terdaftar di class ini (tidak mempengaruhi
        macro milik class lain yang juga inherit Macroable).
        [EN] Remove every macro registered on this class (does not affect
        macros belonging to other classes that also inherit Macroable).
        """
        for name in list(cls._get_own_macros().keys()):
            cls._get_own_macros().pop(name, None)
            if name in cls.__dict__:
                delattr(cls, name)

    # ─── Internals ────────────────────────────────────────────────────────────

    @classmethod
    def _get_own_macros(cls) -> Dict[str, Callable]:
        """
        [ID] Ambil dict macro milik class ini sendiri (bukan diwariskan dari
        parent), dibuat lazily dan disimpan sebagai atribut class privat.

        [EN] Get the macro dict that belongs strictly to this class (not
        inherited from a parent), created lazily and stored as a private
        class attribute.
        """
        # Use cls.__dict__ to ensure each subclass gets its own isolated
        # macro registry instead of sharing/mutating a parent's dict.
        if '_macros' not in cls.__dict__:
            cls._macros = {}
        return cls._macros

    @classmethod
    def _make_macro_method(cls, name: str) -> Callable:
        """Build the actual instance method that dispatches to the registered macro callback."""
        def method(self, *args, **kwargs):
            macro_fn = type(self)._get_own_macros()[name]
            return macro_fn(self, *args, **kwargs)
        method.__name__ = name
        method.__qualname__ = f"{cls.__name__}.{name}"
        return method
