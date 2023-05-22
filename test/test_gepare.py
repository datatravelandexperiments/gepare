# SPDX-License-Identifier: MIT
"""Test gepare."""

import io
import json

from pathlib import Path

import pytest

import gepare
import testutil

XDG_CONFIG_HOME = '/home/test/.config'
XDG_DATA_HOME = '/home/test/.local/share'
XDG_STATE_HOME = '/home/test/.local/state'
XDG_CACHE_HOME = '/home/test/.cache'

@pytest.fixture(name='setup')
def _setup(monkeypatch):
    monkeypatch.setenv('XDG_CONFIG_HOME', XDG_CONFIG_HOME)
    monkeypatch.setenv('XDG_DATA_HOME', XDG_DATA_HOME)
    monkeypatch.setenv('XDG_STATE_HOME', XDG_STATE_HOME)
    monkeypatch.setenv('XDG_CACHE_HOME', XDG_CACHE_HOME)
    monkeypatch.setattr(Path, 'is_dir', lambda _: True)
    monkeypatch.setattr(Path, 'cwd', lambda: Path('/cwd'))

def test_read_inputs_env(setup):
    packages, gcm, config = gepare.read_inputs([io.BytesIO()])
    assert packages == {}
    assert config == {}
    assert gcm['XDG_CONFIG_HOME'] == XDG_CONFIG_HOME
    assert gcm['CONFIG_HOME'] == XDG_CONFIG_HOME

def test_read_inputs_global(setup):
    toml = b'[global]\nvar = "value"'
    packages, gcm, config = gepare.read_inputs([io.BytesIO(toml)])
    assert packages == {}
    assert gcm['var'] == 'value'
    assert config['global']['var'] == 'value'

def test_read_inputs_package(setup):
    key = 'gepare'
    src = f'https://codeberg.org/datatravelandexperiments/{key}'
    dst = f'/usr/local/src/{key}'
    tomls = f"""
        [package.{key}]
        vcs = 'git'
        src = '{src}'
        dst = '{dst}'
    """
    toml = bytes(tomls, encoding='ascii')
    packages, _, _ = gepare.read_inputs([io.BytesIO(toml)])
    p = packages[key]
    assert p.name == key
    assert p.info['src'] == src
    assert str(p.info['dst']) == dst
    assert isinstance(p.origin, gepare.GitOrigin)
    assert p.origin.name == key
    assert p.origin.remote == src
    assert str(p.origin.local) == dst

def test_read_inputs_package_default_dst(setup):
    key = 'gepare'
    src = f'https://codeberg.org/datatravelandexperiments/{key}'
    dst = f'/cwd/{key}'
    tomls = f"""
        [package.{key}]
        vcs = 'hg'
        src = '{src}'
    """
    toml = bytes(tomls, encoding='ascii')
    packages, _, _ = gepare.read_inputs([io.BytesIO(toml)])
    p = packages[key]
    assert p.name == key
    assert p.info['src'] == src
    assert str(p.info['dst']) == dst
    assert isinstance(p.origin, gepare.MercurialOrigin)
    assert p.origin.name == key
    assert p.origin.remote == src
    assert str(p.origin.local) == dst

def test_read_inputs_package_no_src(setup, capsys):
    toml = b"[package.one]\nvcs = 'hg'\n"
    packages, _, _ = gepare.read_inputs([io.BytesIO(toml)])
    assert packages == {}
    err = capsys.readouterr().err
    assert 'missing' in err
    assert 'src' in err

def test_read_inputs_package_no_vcs(setup, capsys):
    toml = b"[package.one]\nsrc = 'http://example.com/'\n"
    packages, _, _ = gepare.read_inputs([io.BytesIO(toml)])
    assert packages == {}
    err = capsys.readouterr().err
    assert 'missing' in err
    assert 'vcs' in err

def test_read_inputs_package_unknown_vcs(setup, capsys):
    toml = b"[package.one]\nsrc = 'http://example.com/'\nvcs = 'wtf'\n"
    packages, _, _ = gepare.read_inputs([io.BytesIO(toml)])
    assert packages == {}
    err = capsys.readouterr().err
    assert 'wtf' in err

def test_build_output(setup):
    key = 'gepare'
    src = f'https://codeberg.org/datatravelandexperiments/{key}'
    dst = f'/usr/local/src/{key}'
    tomls = f"""
        [global]
        gv = 1
        gw = 2

        [package.{key}]
        vcs = 'git'
        src = '{src}'
        dst = '{dst}'
        pv = 3
        pw = 4

        [output]
        global.keys = ['gv']
        global.items = {{gz = '{{gw}}{{gw}}'}}
        package.keys = ['pv']
        package.items = {{pz = '{{pw}}{{pw}}'}}
    """
    toml = bytes(tomls, encoding='ascii')
    packages, gcm, config = gepare.read_inputs([io.BytesIO(toml)])
    out = gepare.build_output(packages, gepare.Expander(gcm), config)
    assert out == {
        'CONFIG_HOME': XDG_CONFIG_HOME,
        'DATA_HOME': XDG_DATA_HOME,
        'STATE_HOME': XDG_STATE_HOME,
        'CACHE_HOME': XDG_CACHE_HOME,
        'gv': 1,
        'gz': '22',
        'package': {
            key: {
                'load': True,
                'name': key,
                'src': src,
                'dst': dst,
                'vcs': 'git',
                'pv': 3,
                'pz': '44',
            },
        },
    }

TOML1 = b"""
    [global]
    gv = '@'
    gw = '#'

    [package.a]
    name = 'gepare'
    src = 'https://codeberg.org/datatravelandexperiments/gepare.git'
    dst = '/usr/local/src/gepare'
    pv = 3
    pw = 4

    [package.b]
    load = false
    vcs = 'hg'
    src = 'https://example.com/public/repo/test'
    dst = '/usr/local/src/test'
    pv = 5
    pw = 6

    [package.c]
    load = 'one'
    vcs = 'ln'
    src = '/usr/local/src/another/share/config'
    dst = '{CONFIG_HOME}/{name}'
    pv = 7
    pw = 8

    [package.d]
    load = ['one', 'two']
    vcs = 'ln'
    src = '/etc/passwd'
    dst = '{DATA_HOME}/passwd'
    pv = 9
    pw = 10

    [output]
    global.keys = ['gv']

    [list.test]
    global.keys = ['gv']
    global.items = {gz = '{gw}{gw}'}
    package.keys = ['pv']
    package.items = {pz = '{pw}{name}{pw}'}

    [list.one]
    file = 'one.txt'
    package.items.pz = 'enable("{name}", {pv})'

    [list.two]
    file = 'two.txt'
    global.keys = ['CONFIG_HOME', 'DATA_HOME']
"""

def test_build_list(setup):
    packages, gcm, config = gepare.read_inputs([io.BytesIO(TOML1)])
    test = gepare.build_list('test', packages, gepare.Expander(gcm), config)
    assert test == ('@\n##\n'
                    '3\n4gepare4\n')
    one = gepare.build_list('one', packages, gepare.Expander(gcm), config)
    assert one == ('enable("gepare", 3)\n'
                   'enable("c", 7)\n'
                   'enable("d", 9)\n')
    two = gepare.build_list('two', packages, gepare.Expander(gcm), config)
    assert two == ('/home/test/.config\n'
                   '/home/test/.local/share\n')

def test_gepa_load(setup, monkeypatch):
    fake_open, opened = testutil.make_mapped({'test.toml': io.BytesIO(TOML1)})
    monkeypatch.setattr(Path, 'open', fake_open)
    r = gepare.main(['gepare', 'test.toml'])
    assert opened == ['test.toml']
    assert r == 0

def test_gepa_load_type_error(setup, monkeypatch):
    monkeypatch.setattr(
        Path, 'open',
        testutil.fake_mapped(
            {'test.toml': io.BytesIO(b'[package.a]\nload = 1\n')}))
    with pytest.raises(TypeError):
        _ = gepare.main(['gepare', 'test.toml'])

def test_gepa_define(setup, monkeypatch, capsys):
    monkeypatch.setattr(Path, 'open',
                        testutil.fake_mapped({'test.toml': io.BytesIO(TOML1)}))
    r = gepare.main(['gepare', '-j', '-D', 'global.gv', 'three', 'test.toml'])
    assert r == 0
    oe = capsys.readouterr()
    j = json.loads(oe.out)
    assert j['gv'] == 'three'

def test_gepa_package(setup, monkeypatch, capsys):
    monkeypatch.setattr(Path, 'open',
                        testutil.fake_mapped({'test.toml': io.BytesIO(TOML1)}))
    r = gepare.main(['gepare', '-j', '-p', 'a', '-p', 'd', 'test.toml'])
    assert r == 0
    j = json.loads(capsys.readouterr().out)
    assert set(j['package'].keys()) == {'a', 'd'}

def test_gepa_unknown_package(setup, monkeypatch, capsys):
    monkeypatch.setattr(Path, 'open',
                        testutil.fake_mapped({'test.toml': io.BytesIO(TOML1)}))
    r = gepare.main(['gepare', '-j', '-p', 'a', '-p', 'xyzzy', 'test.toml'])
    assert r == 0
    oe = capsys.readouterr()
    assert 'xyzzy' in oe.err
    j = json.loads(oe.out)
    assert set(j['package'].keys()) == set('a')

def test_gepa_list(setup, monkeypatch, capsys):
    one = testutil.stringio()
    two = testutil.stringio()
    fake_open, opened = testutil.make_mapped({
        'test.toml': io.BytesIO(TOML1),
        'one.txt': one,
        'two.txt': two,
    })
    fake_exists = testutil.fake_mapped({'.': True}, default=False)
    monkeypatch.setattr(Path, 'open', fake_open)
    monkeypatch.setattr(Path, 'exists', fake_exists)
    r = gepare.main(['gepare', '-l', 'test.toml'])
    assert r == 0
    assert set(opened) == {'test.toml', 'one.txt', 'two.txt'}
    oe = capsys.readouterr()
    assert 'Missing file for list type ‘test’' in oe.err
    assert one.getvalue() == ('enable("gepare", 3)\n'
                              'enable("c", 7)\n'
                              'enable("d", 9)\n')
    assert two.getvalue() == '/home/test/.config\n/home/test/.local/share\n'

def test_gepa_list_select(setup, monkeypatch, capsys):
    one = testutil.stringio()
    two = testutil.stringio()
    monkeypatch.setattr(
        Path, 'open',
        testutil.fake_mapped({
            'test.toml': io.BytesIO(TOML1),
            'one.txt': one,
            'two.txt': two,
        }))
    monkeypatch.setattr(Path, 'exists', testutil.fake_mapped({'.': True},
                                                             default=False))
    r = gepare.main(['gepare', '-L', 'two', 'test.toml'])
    assert r == 0
    assert capsys.readouterr().err == ''
    assert one.getvalue() == ''
    assert two.getvalue() == '/home/test/.config\n/home/test/.local/share\n'

def test_gepa_list_backup_exists(setup, monkeypatch):
    monkeypatch.setattr(
        Path, 'open',
        testutil.fake_mapped({
            'test.toml': io.BytesIO(TOML1),
            'two.txt': testutil.stringio(),
        }))
    fake_exists = testutil.fake_mapped(
        {
            '.': True,
            'two.bak': True,
            'two.txt': True,
        }, default=False)
    fake_unlink, unlinked = testutil.make_none()
    fake_rename, renamed = testutil.make_none()
    monkeypatch.setattr(Path, 'exists', fake_exists)
    monkeypatch.setattr(Path, 'unlink', fake_unlink)
    monkeypatch.setattr(Path, 'rename', fake_rename)
    r = gepare.main(['gepare', '-L', 'two', 'test.toml'])
    assert r == 0
    assert str(unlinked[0][0]) == 'two.bak'
    assert str(renamed[0][0]) == 'two.txt'
    assert str(renamed[0][1]) == 'two.bak'

def test_gepa_list_backup_new(setup, monkeypatch):
    monkeypatch.setattr(
        Path, 'open',
        testutil.fake_mapped({
            'test.toml': io.BytesIO(TOML1),
            'two.txt': testutil.stringio(),
        }))
    fake_exists = testutil.fake_mapped(
        {
            '.': True,
            'two.txt': True,
        }, default=False)
    fake_unlink, unlinked = testutil.make_none()
    fake_rename, renamed = testutil.make_none()
    monkeypatch.setattr(Path, 'exists', fake_exists)
    monkeypatch.setattr(Path, 'unlink', fake_unlink)
    monkeypatch.setattr(Path, 'rename', fake_rename)
    r = gepare.main(['gepare', '-L', 'two', 'test.toml'])
    assert r == 0
    assert not unlinked
    assert str(renamed[0][0]) == 'two.txt'
    assert str(renamed[0][1]) == 'two.bak'

def test_gepa_list_bootstrap(setup, monkeypatch, capsys):
    monkeypatch.setattr(Path, 'open',
                        testutil.fake_mapped({'test.toml': io.BytesIO(TOML1)}))
    r = gepare.main(['gepare', '-b', 'test.toml'])
    assert r == 0
    oe = capsys.readouterr()
    assert oe.out == (
        'mkdir -p "/usr/local/src"\n'
        'if test -d "/usr/local/src/gepare"\n'
        'then (cd "/usr/local/src/gepare" && git pull --rebase)\n'
        'else git clone'
        ' "https://codeberg.org/datatravelandexperiments/gepare.git"'
        ' "/usr/local/src/gepare"\n'
        'fi\n'
        'mkdir -p "/home/test/.config"\n'
        'test -d "/home/test/.config/c" || '
        'ln -s "/usr/local/src/another/share/config" "/home/test/.config/c"\n'
        'mkdir -p "/home/test/.local/share"\n'
        'test -d "/home/test/.local/share/passwd" || '
        'ln -s "/etc/passwd" "/home/test/.local/share/passwd"\n')

def test_gepa_list_bootstrap_all(setup, monkeypatch, capsys):
    monkeypatch.setattr(Path, 'open',
                        testutil.fake_mapped({'test.toml': io.BytesIO(TOML1)}))
    r = gepare.main(['gepare', '-a', '-b', 'test.toml'])
    assert r == 0
    oe = capsys.readouterr()
    assert oe.out == (
        'mkdir -p "/usr/local/src"\n'
        'if test -d "/usr/local/src/gepare"\n'
        'then (cd "/usr/local/src/gepare" && git pull --rebase)\n'
        'else git clone'
        ' "https://codeberg.org/datatravelandexperiments/gepare.git"'
        ' "/usr/local/src/gepare"\n'
        'fi\n'
        'mkdir -p "/usr/local/src"\n'
        'if test -d "/usr/local/src/test"\n'
        'then (cd "/usr/local/src/test" && hg pull -u)\n'
        'else hg clone "https://example.com/public/repo/test"'
        ' "/usr/local/src/test"\n'
        'fi\n'
        'mkdir -p "/home/test/.config"\n'
        'test -d "/home/test/.config/c" ||'
        ' ln -s "/usr/local/src/another/share/config"'
        ' "/home/test/.config/c"\n'
        'mkdir -p "/home/test/.local/share"\n'
        'test -d "/home/test/.local/share/passwd" ||'
        ' ln -s "/etc/passwd" "/home/test/.local/share/passwd"\n')
