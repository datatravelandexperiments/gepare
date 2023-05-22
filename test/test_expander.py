# SPDX-License-Identifier: MIT
"""Test Expander."""

from gepare import Expander

EXPANSIONS = {
    'a': 'A',
    'b': '{a}-{a}',
    'c': '{b}={b}',
}

def test_expander_get_plain():
    e = Expander(EXPANSIONS)
    assert e.get('a') == 'A'

def test_expander_get_format():
    e = Expander(EXPANSIONS)
    assert e.get('b') == 'A-A'

def test_expander_get_recursive():
    e = Expander(EXPANSIONS)
    assert e.get('c') == 'A-A=A-A'

def test_expander_get_missing():
    e = Expander(EXPANSIONS)
    assert e.get('test') is None

def test_expander_get_default():
    e = Expander(EXPANSIONS)
    assert e.get('test', 9832) == 9832

def test_expander_contains():
    e = Expander(EXPANSIONS)
    assert 'c' in e
    assert 'd' not in e
