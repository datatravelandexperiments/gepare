# SPDX-License-Identifier: MIT
"""Test XDG utilties."""

from pathlib import Path

from gepare import xdg_dir

def test_xdg_dir_env_exists(monkeypatch):
    d1 = '/home/test'
    monkeypatch.setenv('XDG_TEST_HOME', d1)
    monkeypatch.setattr(Path, 'is_dir', lambda _: True)
    assert xdg_dir('TEST', 'none') == Path(d1)

def test_xdg_dir_env_mkdir(monkeypatch):
    d1 = '/home/test'
    p1 = ''

    def mkdir(p: Path, **_):
        nonlocal p1
        p1 = str(p)

    monkeypatch.setenv('XDG_TEST_HOME', d1)
    monkeypatch.setattr(Path, 'is_dir', lambda _: False)
    monkeypatch.setattr(Path, 'mkdir', mkdir)
    assert xdg_dir('TEST', 'none') == Path(d1)
    assert p1 == d1

def test_xdg_dir_default_exists(monkeypatch):
    d1 = '/home/test'
    monkeypatch.setattr(Path, 'is_dir', lambda _: True)
    assert xdg_dir('TEST', d1) == Path(d1)

def test_xdg_dir_default_mkdir(monkeypatch):
    d1 = '/home/test'
    p1 = ''

    def mkdir(p: Path, **_):
        nonlocal p1
        p1 = str(p)

    monkeypatch.setattr(Path, 'is_dir', lambda _: False)
    monkeypatch.setattr(Path, 'mkdir', mkdir)
    assert xdg_dir('TEST', d1) == Path(d1)
    assert p1 == d1
