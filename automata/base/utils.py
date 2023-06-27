#!/usr/bin/env python3
"""Miscellaneous utility functions and classes."""

from collections import defaultdict
from itertools import count
from typing import Any, Callable, Dict, Generic, Iterable, List, Set, Tuple, TypeVar

from frozendict import frozendict


def freeze_value(value: Any) -> Any:
    """
    A helper function to convert the given value / structure into a fully
    immutable one by recursively processing said structure and any of its
    members, freezing them as well
    """
    if isinstance(value, (str, int)):
        return value
    if isinstance(value, dict):
        return frozendict(
            {
                dict_key: freeze_value(dict_value)
                for dict_key, dict_value in value.items()
            }
        )
    if isinstance(value, set):
        return frozenset(freeze_value(element) for element in value)
    if isinstance(value, list):
        return tuple(freeze_value(element) for element in value)
    return value


def get_renaming_function(counter: count) -> Callable[[Any], int]:
    """
    A helper function that returns a renaming function to be used in the creation of
    other automata. The parameter counter should be an itertools count.
    This helper function will return the same distinct output taken from counter
    for each distinct input.
    """

    return defaultdict(counter.__next__).__getitem__
