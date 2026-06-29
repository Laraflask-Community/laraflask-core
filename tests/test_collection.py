"""Tests for laraflask.core.collection.Collection."""

import pytest

from laraflask.core.collection import Collection


class TestCollectionConstruction:
    """Test various ways to construct a Collection."""

    def test_make_from_list(self):
        c = Collection.make([1, 2, 3])
        assert c.all() == [1, 2, 3]

    def test_make_from_none(self):
        c = Collection.make(None)
        assert c.all() == []

    def test_make_from_dict(self):
        c = Collection.make({"a": 1, "b": 2})
        assert c.all() == {"a": 1, "b": 2}

    def test_make_from_another_collection(self):
        original = Collection([10, 20])
        copy = Collection.make(original)
        assert copy.all() == [10, 20]

    def test_times_with_callback(self):
        c = Collection.times(3, lambda i: i * 10)
        assert c.all() == [10, 20, 30]

    def test_times_without_callback(self):
        c = Collection.times(4)
        assert c.all() == [1, 2, 3, 4]

    def test_range(self):
        c = Collection.range(2, 5)
        assert c.all() == [2, 3, 4, 5]


class TestCollectionTransformation:
    """Test transformation methods: map, filter, reject, reduce, pluck, flatten, unique."""

    def test_map(self):
        c = Collection([1, 2, 3]).map(lambda x: x * 2)
        assert c.all() == [2, 4, 6]

    def test_map_on_dict(self):
        c = Collection({"a": 1, "b": 2}).map(lambda x: x + 10)
        assert c.all() == {"a": 11, "b": 12}

    def test_filter(self):
        c = Collection([1, 2, 3, 4, 5]).filter(lambda x: x > 3)
        assert c.all() == [4, 5]

    def test_filter_default_truthy(self):
        c = Collection([0, 1, "", "hello", None, True]).filter()
        assert c.all() == [1, "hello", True]

    def test_reject(self):
        c = Collection([1, 2, 3, 4]).reject(lambda x: x % 2 == 0)
        assert c.all() == [1, 3]

    def test_reduce(self):
        result = Collection([1, 2, 3, 4]).reduce(lambda carry, item: carry + item, 0)
        assert result == 10

    def test_pluck(self):
        items = [{"name": "Alice", "age": 30}, {"name": "Bob", "age": 25}]
        c = Collection(items).pluck("name")
        assert c.all() == ["Alice", "Bob"]

    def test_pluck_with_key_by(self):
        items = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
        c = Collection(items).pluck("name", "id")
        assert c.all() == {1: "Alice", 2: "Bob"}

    def test_flatten(self):
        c = Collection([[1, 2], [3, [4, 5]]]).flatten()
        assert c.all() == [1, 2, 3, 4, 5]

    def test_flatten_with_depth(self):
        c = Collection([[1, [2, 3]], [4, [5]]]).flatten(depth=1)
        assert c.all() == [1, [2, 3], 4, [5]]

    def test_unique(self):
        c = Collection([1, 2, 2, 3, 3, 3]).unique()
        assert c.all() == [1, 2, 3]

    def test_unique_with_key(self):
        items = [{"id": 1, "v": "a"}, {"id": 2, "v": "b"}, {"id": 1, "v": "c"}]
        c = Collection(items).unique("id")
        assert len(c.all()) == 2

    def test_merge_lists(self):
        c = Collection([1, 2]).merge([3, 4])
        assert c.all() == [1, 2, 3, 4]

    def test_merge_dicts(self):
        c = Collection({"a": 1}).merge({"b": 2})
        assert c.all() == {"a": 1, "b": 2}


class TestCollectionOrdering:
    """Test ordering and grouping methods."""

    def test_sort_by_callback(self):
        c = Collection([3, 1, 2]).sort_by(lambda x: x)
        assert c.all() == [1, 2, 3]

    def test_sort_by_key(self):
        items = [{"name": "Charlie"}, {"name": "Alice"}, {"name": "Bob"}]
        c = Collection(items).sort_by("name")
        assert c.all()[0]["name"] == "Alice"

    def test_sort_by_desc(self):
        c = Collection([1, 2, 3]).sort_by_desc(lambda x: x)
        assert c.all() == [3, 2, 1]

    def test_group_by(self):
        items = [
            {"type": "a", "val": 1},
            {"type": "b", "val": 2},
            {"type": "a", "val": 3},
        ]
        grouped = Collection(items).group_by("type")
        assert "a" in grouped.all()
        assert grouped.all()["a"].count() == 2

    def test_chunk(self):
        c = Collection([1, 2, 3, 4, 5]).chunk(2)
        chunks = c.all()
        assert len(chunks) == 3
        assert chunks[0].all() == [1, 2]
        assert chunks[2].all() == [5]

    def test_reverse(self):
        c = Collection([1, 2, 3]).reverse()
        assert c.all() == [3, 2, 1]

    def test_take_positive(self):
        c = Collection([1, 2, 3, 4, 5]).take(3)
        assert c.all() == [1, 2, 3]

    def test_take_negative(self):
        c = Collection([1, 2, 3, 4, 5]).take(-2)
        assert c.all() == [4, 5]


class TestCollectionInspection:
    """Test inspection methods: first, last, count, is_empty, contains."""

    def test_first(self):
        c = Collection([10, 20, 30])
        assert c.first() == 10

    def test_first_with_callback(self):
        c = Collection([1, 2, 3, 4])
        assert c.first(lambda x: x > 2) == 3

    def test_first_default(self):
        c = Collection([])
        assert c.first(default="none") == "none"

    def test_last(self):
        c = Collection([10, 20, 30])
        assert c.last() == 30

    def test_last_with_callback(self):
        c = Collection([1, 2, 3, 4])
        assert c.last(lambda x: x < 3) == 2

    def test_count(self):
        assert Collection([1, 2, 3]).count() == 3

    def test_is_empty(self):
        assert Collection([]).is_empty() is True
        assert Collection([1]).is_empty() is False

    def test_is_not_empty(self):
        assert Collection([1]).is_not_empty() is True
        assert Collection([]).is_not_empty() is False

    def test_contains_value(self):
        c = Collection([1, 2, 3])
        assert c.contains(2) is True
        assert c.contains(99) is False

    def test_contains_callback(self):
        c = Collection([1, 2, 3])
        assert c.contains(callback=lambda x: x == 3) is True
        assert c.contains(callback=lambda x: x > 10) is False


class TestCollectionAggregation:
    """Test aggregation methods: sum, avg, min, max."""

    def test_sum(self):
        assert Collection([1, 2, 3, 4]).sum() == 10

    def test_sum_with_key(self):
        items = [{"price": 10}, {"price": 20}]
        assert Collection(items).sum("price") == 30

    def test_avg(self):
        assert Collection([2, 4, 6]).avg() == 4.0

    def test_avg_empty(self):
        assert Collection([]).avg() == 0

    def test_min(self):
        c = Collection([5, 3, 8, 1])
        assert c.min() == 1

    def test_max(self):
        c = Collection([5, 3, 8, 1])
        assert c.max() == 8


class TestCollectionUtilities:
    """Test utility methods: tap, pipe, when, each."""

    def test_tap(self):
        side_effects = []
        result = Collection([1, 2, 3]).tap(lambda c: side_effects.append(c.count()))
        assert side_effects == [3]
        assert result.all() == [1, 2, 3]

    def test_pipe(self):
        result = Collection([1, 2, 3]).pipe(lambda c: c.sum())
        assert result == 6

    def test_when_true(self):
        c = Collection([1, 2, 3]).when(True, lambda c: c.filter(lambda x: x > 1))
        assert c.all() == [2, 3]

    def test_when_false(self):
        c = Collection([1, 2, 3]).when(False, lambda c: c.filter(lambda x: x > 1))
        assert c.all() == [1, 2, 3]

    def test_each(self):
        collected = []
        Collection([1, 2, 3]).each(lambda x: collected.append(x))
        assert collected == [1, 2, 3]

    def test_each_stops_on_false(self):
        collected = []

        def cb(x):
            collected.append(x)
            if x == 2:
                return False

        Collection([1, 2, 3]).each(cb)
        assert collected == [1, 2]


class TestCollectionProtocol:
    """Test Python protocol methods: __iter__, __len__, __getitem__, __contains__, __bool__."""

    def test_iter(self):
        assert list(Collection([1, 2, 3])) == [1, 2, 3]

    def test_len(self):
        assert len(Collection([1, 2, 3])) == 3

    def test_getitem(self):
        c = Collection([10, 20, 30])
        assert c[1] == 20

    def test_contains_operator(self):
        c = Collection([1, 2, 3])
        assert 2 in c
        assert 99 not in c

    def test_bool(self):
        assert bool(Collection([1])) is True
        assert bool(Collection([])) is False

    def test_eq(self):
        a = Collection([1, 2, 3])
        b = Collection([1, 2, 3])
        assert a == b
