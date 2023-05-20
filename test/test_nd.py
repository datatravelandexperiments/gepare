# SPDX-License-Identifier: MIT

import pytest

from gepare import ndget, ndupdate

D0 = {
    'v0': 0,
    'w0': 0,
    'd0': {
        'd1': {
            'v2': 2,
        },
        'l1': [1, 2, 3],
        's1': set((10, 11, 12)),
    }
}

D1 = {
    'w0': 2,
    'd0': {
        'd1': {
            'v3': 3,
        },
        'l1': [4, 5],
        's1': set((13, 14)),
        'v1': 100,
    }
}

def test_ndget_top():
    assert ndget(D0, ['w0']) == 0

def test_ndget_inner():
    assert ndget(D0, ['d0', 'd1', 'v2']) == 2

def test_ndget_top_missing():
    assert ndget(D0, ['zz']) is None

def test_ndget_inner_missing():
    assert ndget(D0, ['d0', 'd1', 'zz']) is None

def test_ndget_non_container():
    assert ndget(D0, ['v0', 'v1']) is None

def test_ndupdate():
    d = D0.copy()
    ndupdate(d, D1)
    assert d['v0'] == 0
    assert d['w0'] == 2
    assert d['d0']['d1'] == {'v2': 2, 'v3': 3}
    assert d['d0']['l1'] == [1,2,3,4,5]
    assert d['d0']['s1'] == set(range(10, 15))
    assert d['d0']['v1'] == 100

def test_ndupdate_mismatch():
    d = D0.copy()
    with pytest.raises(TypeError):
        ndupdate(d, {'d0': {'d1': {'v2': 'test'}}})
