import itertools
import pytest

from modules.pages import parse_page_spec, describe_pages, navigation_steps, all_pages


@pytest.mark.parametrize("spec", [None, "", "  ", "all", "ALL"])
def test_all_pages_means_none(spec):
    assert parse_page_spec(spec) is None


def test_single_and_range():
    assert parse_page_spec("5") == [5]
    assert parse_page_spec("1-10") == list(range(1, 11))


def test_disjoint_selection_is_preserved_exactly():
    # Regression: this used to collapse to 3..9 and capture pages 4-6 as well.
    assert parse_page_spec("3,7-9") == [3, 7, 8, 9]
    assert parse_page_spec("10, 2-3 ,10") == [2, 3, 10]


@pytest.mark.parametrize("spec", ["abc", "3-x", "9-7", "0", "-1", "1-"])
def test_invalid_specs_raise(spec):
    with pytest.raises(ValueError):
        parse_page_spec(spec)


def test_describe_pages():
    assert describe_pages([3, 7, 8, 9]) == "3, 7-9"
    assert describe_pages([1]) == "1"
    assert describe_pages([]) == ""


def test_navigation_steps_use_next_only_for_consecutive_pages():
    assert list(navigation_steps([3, 7, 8, 9])) == [(3, "jump"), (7, "jump"), (8, "next"), (9, "next")]
    assert list(navigation_steps([1, 2, 3])) == [(1, "jump"), (2, "next"), (3, "next")]


def test_navigation_steps_open_ended_is_capped():
    steps = list(navigation_steps(itertools.count(1), limit=4))
    assert steps == [(1, "jump"), (2, "next"), (3, "next"), (4, "next")]


def test_all_pages_targets():
    assert list(all_pages(3)) == [1, 2, 3]
    assert next(iter(all_pages(None))) == 1
