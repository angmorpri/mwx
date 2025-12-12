# 2025/09/10
"""
test_01_util.py - Tests for the utility functions
"""

from datetime import datetime

import pytest

from mwx.util import find, find_first


class Person:
    def __init__(self, name: str, birthday: datetime, city: str):
        self.name = name
        self.birthday = birthday
        self.city = city

    @property
    def age(self) -> int:
        return datetime.today().year - self.birthday.year


@pytest.fixture
def sample_people():
    return [
        Person("Alice", datetime(1990, 5, 1), "New York"),
        Person("Bob", datetime(1985, 8, 20), "Los Angeles"),
        Person("Charlie", datetime(1996, 12, 15), "New York"),
        Person("Diana", datetime(1988, 3, 30), "Chicago"),
    ]


# Testing


def test_find_one_pos_cond(sample_people):
    results = find(sample_people, lambda p: p.name.startswith("A"))
    assert len(results) == 1
    assert results[0].name == "Alice"


def test_find_multiple_pos_conds(sample_people):
    results = find(sample_people, lambda p: p.city == "New York", lambda p: p.age < 30)
    assert len(results) == 1
    assert results[0].name == "Charlie"


def test_find_one_kwarg_cond(sample_people):
    results = find(sample_people, city="Chicago")
    assert len(results) == 1
    assert results[0].name == "Diana"


def test_find_multiple_kwarg_conds(sample_people):
    results = find(sample_people, city="New York", name="Charlie")
    assert len(results) == 1
    assert results[0].name == "Charlie"


def test_find_pos_and_kwarg_conds(sample_people):
    results = find(sample_people, lambda p: p.age > 25, city="New York")
    assert len(results) == 2
    names = {p.name for p in results}
    assert names == {"Alice", "Charlie"}


def test_find_no_matches(sample_people):
    results = find(sample_people, lambda p: p.name == "Eve")
    assert len(results) == 0


def test_find_first_no_matches(sample_people):
    result = find_first(sample_people, lambda p: p.name == "Eve")
    assert result is None


def test_find_first_with_matches(sample_people):
    result = find_first(sample_people, city="New York")
    assert result is not None
    assert result.name in {"Alice", "Charlie"}
