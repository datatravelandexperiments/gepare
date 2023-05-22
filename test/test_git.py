# SPDX-License-Identifier: MIT
"""Test git origin."""

import subprocess

from pathlib import Path

import testutil

import gepare

def test_boostrap(capsys):
    local = '/usr/local/src/test'
    remote = 'remote'

    g = gepare.GitOrigin('test', remote, Path(local))
    assert g.bootstrap()
    assert capsys.readouterr().out == (
        'mkdir -p "/usr/local/src"\n'
        f'if test -d "{local}"\n'
        f'then (cd "{local}" && git pull --rebase)\n'
        f'else git clone "{remote}" "{local}"\n'
        'fi\n')

def test_clone(monkeypatch):
    local = 'local'
    remote = 'remote'
    fake_run, runs = testutil.make_run()
    monkeypatch.setattr(subprocess, 'run', fake_run)
    monkeypatch.setattr(Path, 'exists', lambda _: False)
    monkeypatch.setattr(Path, 'is_dir', lambda _: True)

    g = gepare.GitOrigin('test', remote, Path(local))
    assert g.clone()
    assert runs[0].args == ['git', 'clone', remote, local]

def test_refresh(monkeypatch):
    local = 'local'
    remote = 'remote'
    fake_run, runs = testutil.make_run()
    monkeypatch.setattr(subprocess, 'run', fake_run)
    monkeypatch.setattr(Path, 'exists', lambda _: True)
    monkeypatch.setattr(Path, 'is_dir', lambda _: True)

    g = gepare.GitOrigin('test', remote, Path(local))
    assert g.update()
    assert runs[0].args == ['git', 'pull', '--rebase']

def test_status(monkeypatch):
    local = 'local'
    remote = 'remote'
    fake_run, runs = testutil.make_run()
    monkeypatch.setattr(subprocess, 'run', fake_run)
    monkeypatch.setattr(Path, 'exists', lambda _: True)
    monkeypatch.setattr(Path, 'is_dir', lambda _: True)

    g = gepare.GitOrigin('test', remote, Path(local))
    assert g.status() == gepare.OriginStatus.UNKNOWN
    assert runs[0].args == ['git', 'status', '--porcelain=2']
