# SPDX-License-Identifier: MIT
"""Test Mercurial origin."""

import subprocess

from pathlib import Path

import testutil

import gepare

def test_boostrap(capsys):
    local = '/usr/local/src/test'
    remote = 'remote'

    g = gepare.MercurialOrigin('test', remote, Path(local))
    assert g.bootstrap()
    assert capsys.readouterr().out == (
        'mkdir -p "/usr/local/src"\n'
        f'if test -d "{local}"\n'
        f'then (cd "{local}" && hg pull -u)\n'
        f'else hg clone "{remote}" "{local}"\n'
        'fi\n')

def test_clone(monkeypatch):
    local = 'local'
    remote = 'remote'
    fake_run, runs = testutil.make_run()
    monkeypatch.setattr(subprocess, 'run', fake_run)
    monkeypatch.setattr(Path, 'exists', lambda _: False)
    monkeypatch.setattr(Path, 'is_dir', lambda _: True)

    g = gepare.MercurialOrigin('test', remote, Path(local))
    assert g.refresh()
    assert runs[0].args == ['hg', 'clone', remote, local]

def test_refresh(monkeypatch):
    local = 'local'
    remote = 'remote'
    fake_run, runs = testutil.make_run()
    monkeypatch.setattr(subprocess, 'run', fake_run)
    monkeypatch.setattr(Path, 'exists', lambda _: True)
    monkeypatch.setattr(Path, 'is_dir', lambda _: True)

    g = gepare.MercurialOrigin('test', remote, Path(local))
    assert g.update()
    assert runs[0].args == ['hg', 'pull', '-u']

def test_status(monkeypatch):
    local = 'local'
    remote = 'remote'
    fake_run, runs = testutil.make_run()
    monkeypatch.setattr(subprocess, 'run', fake_run)
    monkeypatch.setattr(Path, 'exists', lambda _: True)
    monkeypatch.setattr(Path, 'is_dir', lambda _: True)

    g = gepare.MercurialOrigin('test', remote, Path(local))
    assert g.status() == gepare.OriginStatus.UNKNOWN
    assert runs[0].args == ['hg', 'status']
