# SPDX-License-Identifier: MIT
"""Test TOML utilities."""

import io
import pathlib

import testutil

from gepare import read_toml, toml_escape

def test_read_toml_file(monkeypatch):
    monkeypatch.setattr(
        pathlib.Path, 'open',
        testutil.fake_mapped({'file': io.BytesIO(b'key = "value"')}))
    r = read_toml(['file'])
    assert r == {'key': 'value'}

def test_read_toml_stream(monkeypatch):
    toml = b'key = "value"'
    r = read_toml([io.BytesIO(toml)])
    assert r == {'key': 'value'}

def test_toml_escape():
    assert (toml_escape('This is a "test" with \\ and \n, OK?') ==
            r'This is a \u0022test\u0022 with \u005C and \u000A, OK?')
