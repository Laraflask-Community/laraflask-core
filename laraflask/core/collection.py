"""
Laraflask Collection
[ID] Wrapper berantai (chainable) untuk list/dict Python, terinspirasi dari
Illuminate\\Support\\Collection milik Laravel. Memudahkan transformasi data
(map, filter, reduce, dst) dengan gaya method-chaining yang ekspresif.

[EN] A chainable wrapper around Python lists/dicts, inspired by Laravel's
Illuminate\\Support\\Collection. Makes data transformation (map, filter,
reduce, etc.) expressive via fluent method-chaining.
"""

from __future__ import annotations
import functools
from typing import Any, Callable, Dict, Iterable, Iterator, List, Optional, Union


class Collection:
    """
    [ID] Koleksi yang bisa di-chain, membungkus list atau dict Python.
    Mendukung iterasi, indexing, dan operasi umum ala Laravel Collection.

    [EN] A chainable collection wrapping a Python list or dict. Supports
    iteration, indexing, and common operations in the style of Laravel's
    Collection.
    """

    def __init__(self, items: Union[Iterable, Dict, None] = None):
        if items is None:
            items = []
        elif isinstance(items, Collection):
            items = items.all()
        elif isinstance(items, dict):
            items = dict(items)
        else:
            items = list(items)

        self._items = items

    # ─── Construction ─────────────────────────────────────────────────────────

    @classmethod
    def make(cls, items: Union[Iterable, Dict, None] = None) -> 'Collection':
        """Create a new Collection instance. Alias for the constructor."""
        return cls(items)

    @classmethod
    def times(cls, count: int, callback: Callable[[int], Any] = None) -> 'Collection':
        """Create a new Collection by invoking `callback` `count` times (1-indexed)."""
        if callback is None:
            return cls(range(1, count + 1))
        return cls([callback(i) for i in range(1, count + 1)])

    @classmethod
    def range(cls, start: int, end: int) -> 'Collection':
        """Create a Collection containing a range of integers (inclusive)."""
        return cls(range(start, end + 1))

    # ─── Raw Access ───────────────────────────────────────────────────────────

    def all(self) -> Union[List, Dict]:
        """Get the underlying items as a raw list or dict."""
        return self._items

    def to_list(self) -> List:
        """Get the collection's items as a plain Python list."""
        if isinstance(self._items, dict):
            return list(self._items.values())
        return list(self._items)

    def to_dict(self) -> Dict:
        """Get the collection's items as a plain Python dict (index-keyed if it was a list)."""
        if isinstance(self._items, dict):
            return dict(self._items)
        return {i: v for i, v in enumerate(self._items)}

    def values(self) -> 'Collection':
        """Reset the keys on the underlying list/dict, returning a new Collection of values."""
        if isinstance(self._items, dict):
            return Collection(list(self._items.values()))
        return Collection(list(self._items))

    def keys(self) -> 'Collection':
        """Get the keys of the collection's items (dict keys or list indices)."""
        if isinstance(self._items, dict):
            return Collection(list(self._items.keys()))
        return Collection(list(range(len(self._items))))

    # ─── Transformation ───────────────────────────────────────────────────────

    def map(self, callback: Callable[[Any], Any]) -> 'Collection':
        """Apply `callback` to every item, returning a new Collection of results."""
        if isinstance(self._items, dict):
            return Collection({k: callback(v) for k, v in self._items.items()})
        return Collection([callback(item) for item in self._items])

    def map_with_keys(self, callback: Callable[[Any], tuple]) -> 'Collection':
        """Run `callback` over each item, building a new dict-backed Collection from (key, value) pairs."""
        result = {}
        for item in self._iterate_values():
            key, value = callback(item)
            result[key] = value
        return Collection(result)

    def filter(self, callback: Callable[[Any], bool] = None) -> 'Collection':
        """Keep only the items for which `callback` returns truthy (defaults to truthy items)."""
        callback = callback or (lambda item: bool(item))
        if isinstance(self._items, dict):
            return Collection({k: v for k, v in self._items.items() if callback(v)})
        return Collection([item for item in self._items if callback(item)])

    def reject(self, callback: Callable[[Any], bool]) -> 'Collection':
        """Inverse of filter() — keep only items for which `callback` returns falsy."""
        return self.filter(lambda item: not callback(item))

    def reduce(self, callback: Callable[[Any, Any], Any], initial: Any = None) -> Any:
        """Reduce the collection to a single value using `callback(carry, item)`."""
        return functools.reduce(callback, self._iterate_values(), initial)

    def each(self, callback: Callable[[Any], Any]) -> 'Collection':
        """Run `callback` over every item without altering the collection. Returns self for chaining."""
        for item in self._iterate_values():
            if callback(item) is False:
                break
        return self

    def pluck(self, key: str, key_by: Optional[str] = None) -> 'Collection':
        """
        [ID] Ambil nilai dari atribut/key tertentu pada setiap item (dict atau object).
        [EN] Pluck the value of `key` from every item (dict or object).
        """
        def get_value(item, k):
            if isinstance(item, dict):
                return item.get(k)
            return getattr(item, k, None)

        if key_by is None:
            return Collection([get_value(item, key) for item in self._iterate_values()])

        result = {}
        for item in self._iterate_values():
            result[get_value(item, key_by)] = get_value(item, key)
        return Collection(result)

    def flatten(self, depth: int = None) -> 'Collection':
        """Flatten a multi-dimensional collection into a single level (or up to `depth` levels)."""
        def _flatten(items, current_depth):
            result = []
            for item in items:
                if isinstance(item, Collection):
                    item = item.all()
                if isinstance(item, (list, tuple)) and (current_depth is None or current_depth > 0):
                    next_depth = None if current_depth is None else current_depth - 1
                    result.extend(_flatten(item, next_depth))
                else:
                    result.append(item)
            return result

        return Collection(_flatten(self._iterate_values(), depth))

    def unique(self, key: Union[str, Callable] = None) -> 'Collection':
        """Remove duplicate items, optionally comparing by `key` (attribute name or callback)."""
        seen = []
        result = []

        def resolve(item):
            if key is None:
                return item
            if callable(key):
                return key(item)
            if isinstance(item, dict):
                return item.get(key)
            return getattr(item, key, None)

        for item in self._iterate_values():
            marker = resolve(item)
            if marker not in seen:
                seen.append(marker)
                result.append(item)

        return Collection(result)

    def flip(self) -> 'Collection':
        """Swap the collection's keys with their corresponding values (dict-backed collections)."""
        if isinstance(self._items, dict):
            return Collection({v: k for k, v in self._items.items()})
        return Collection({v: i for i, v in enumerate(self._items)})

    def merge(self, other: Union['Collection', Iterable, Dict]) -> 'Collection':
        """Merge another collection/list/dict into this one, returning a new Collection."""
        other_items = other.all() if isinstance(other, Collection) else other

        if isinstance(self._items, dict):
            merged = dict(self._items)
            merged.update(other_items if isinstance(other_items, dict) else dict(enumerate(other_items)))
            return Collection(merged)

        return Collection(list(self._items) + list(other_items))

    # ─── Ordering / Grouping ──────────────────────────────────────────────────

    def sort_by(self, key: Union[str, Callable], reverse: bool = False) -> 'Collection':
        """Sort the collection by `key` (attribute name or callback), returning a new Collection."""
        resolver = key if callable(key) else self._attribute_resolver(key)
        sorted_items = sorted(self._iterate_values(), key=resolver, reverse=reverse)
        return Collection(sorted_items)

    def sort_by_desc(self, key: Union[str, Callable]) -> 'Collection':
        """Sort the collection by `key` in descending order."""
        return self.sort_by(key, reverse=True)

    def group_by(self, key: Union[str, Callable]) -> 'Collection':
        """Group the collection's items by `key` (attribute name or callback)."""
        resolver = key if callable(key) else self._attribute_resolver(key)
        groups: Dict[Any, List] = {}

        for item in self._iterate_values():
            group_key = resolver(item)
            groups.setdefault(group_key, []).append(item)

        return Collection({k: Collection(v) for k, v in groups.items()})

    def chunk(self, size: int) -> 'Collection':
        """Split the collection into chunks of `size`, returning a Collection of Collections."""
        items = self._iterate_values()
        chunks = [Collection(items[i:i + size]) for i in range(0, len(items), size)]
        return Collection(chunks)

    def reverse(self) -> 'Collection':
        """Reverse the order of the collection's items."""
        return Collection(list(reversed(self._iterate_values())))

    def take(self, count: int) -> 'Collection':
        """Take the first `count` items (or last `count` if negative)."""
        items = self._iterate_values()
        if count < 0:
            return Collection(items[count:])
        return Collection(items[:count])

    # ─── Inspection ───────────────────────────────────────────────────────────

    def contains(self, value: Any = None, callback: Callable[[Any], bool] = None) -> bool:
        """Determine whether the collection contains `value`, or any item matching `callback`."""
        if callback is not None:
            return any(callback(item) for item in self._iterate_values())
        return value in self._iterate_values()

    def first(self, callback: Callable[[Any], bool] = None, default: Any = None) -> Any:
        """Get the first item, optionally matching `callback`; otherwise `default`."""
        items = self._iterate_values()
        if callback is None:
            return items[0] if items else default
        for item in items:
            if callback(item):
                return item
        return default

    def last(self, callback: Callable[[Any], bool] = None, default: Any = None) -> Any:
        """Get the last item, optionally matching `callback`; otherwise `default`."""
        items = self._iterate_values()
        if callback is None:
            return items[-1] if items else default
        for item in reversed(items):
            if callback(item):
                return item
        return default

    def count(self) -> int:
        """Get the total number of items in the collection."""
        return len(self._items)

    def is_empty(self) -> bool:
        """Determine whether the collection is empty."""
        return len(self._items) == 0

    def is_not_empty(self) -> bool:
        """Determine whether the collection is not empty."""
        return not self.is_empty()

    # ─── Aggregation ──────────────────────────────────────────────────────────

    def sum(self, key: Union[str, Callable] = None) -> Union[int, float]:
        """Sum the collection's values, optionally extracted via `key`."""
        return sum(self._resolve_numeric(item, key) for item in self._iterate_values())

    def avg(self, key: Union[str, Callable] = None) -> Union[int, float]:
        """Average the collection's values, optionally extracted via `key`."""
        items = self._iterate_values()
        if not items:
            return 0
        return self.sum(key) / len(items)

    def min(self, key: Union[str, Callable] = None) -> Any:
        """Get the minimum value in the collection, optionally extracted via `key`."""
        items = self._iterate_values()
        if not items:
            return None
        resolver = key if callable(key) else (self._attribute_resolver(key) if key else (lambda x: x))
        return min(items, key=resolver)

    def max(self, key: Union[str, Callable] = None) -> Any:
        """Get the maximum value in the collection, optionally extracted via `key`."""
        items = self._iterate_values()
        if not items:
            return None
        resolver = key if callable(key) else (self._attribute_resolver(key) if key else (lambda x: x))
        return max(items, key=resolver)

    # ─── Fluent Utilities ─────────────────────────────────────────────────────

    def tap(self, callback: Callable[['Collection'], Any]) -> 'Collection':
        """
        [ID] Jalankan `callback` dengan collection sebagai argumen tanpa
        mengubah hasil chain (mis. untuk debugging/logging di tengah chain).
        [EN] Pass the collection to `callback` for side effects without
        affecting the chain (e.g. debugging/logging mid-chain).
        """
        callback(self)
        return self

    def pipe(self, callback: Callable[['Collection'], Any]) -> Any:
        """Pass the collection to `callback` and return its result (transforms the chain)."""
        return callback(self)

    def when(self, condition: Any, callback: Callable[['Collection'], Any]) -> 'Collection':
        """Apply `callback(self)` only if `condition` is truthy; otherwise return self unchanged."""
        if condition:
            result = callback(self)
            return result if isinstance(result, Collection) else self
        return self

    # ─── Helpers ──────────────────────────────────────────────────────────────

    def _iterate_values(self) -> List:
        """Internal helper: always return a plain list of values, regardless of backing dict/list."""
        if isinstance(self._items, dict):
            return list(self._items.values())
        return list(self._items)

    def _attribute_resolver(self, key: str) -> Callable[[Any], Any]:
        """Build a resolver function for a dict-key or object-attribute lookup."""
        def resolver(item):
            if isinstance(item, dict):
                return item.get(key)
            return getattr(item, key, None)
        return resolver

    def _resolve_numeric(self, item: Any, key: Union[str, Callable] = None) -> Union[int, float]:
        if key is None:
            return item or 0
        if callable(key):
            return key(item) or 0
        if isinstance(item, dict):
            return item.get(key) or 0
        return getattr(item, key, 0) or 0

    # ─── Python Protocol ──────────────────────────────────────────────────────

    def __iter__(self) -> Iterator:
        return iter(self._iterate_values())

    def __len__(self) -> int:
        return len(self._items)

    def __getitem__(self, key: Any) -> Any:
        return self._items[key]

    def __setitem__(self, key: Any, value: Any) -> None:
        self._items[key] = value

    def __contains__(self, value: Any) -> bool:
        return value in self._iterate_values()

    def __bool__(self) -> bool:
        return len(self._items) > 0

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, Collection):
            return self._items == other._items
        return self._items == other

    def __repr__(self) -> str:
        return f"<Collection {self._items!r}>"
