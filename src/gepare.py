#!/usr/bin/env python
# SPDX-License-Identifier: MIT
"""Package loader.

This is self-contained to simplify bootstrapping.
"""

import argparse
import io
import json
import os
import shlex
import subprocess
import sys
import tomllib

from abc import ABC, abstractmethod
from collections import ChainMap
from collections.abc import (Iterable, Mapping, MutableMapping, MutableSequence,
                             MutableSet, Set, Sequence)
from enum import Enum
from pathlib import Path
from typing import Any, Self, Type, TypeVar

T = TypeVar('T')

SELF = 'gepare'

def error(s):
    print(f'{SELF}: {s}', file=sys.stderr)

class Expander:
    """Get from a mapping with lazy recursive format string expansion."""

    def __init__(self, mapping: Mapping):
        self.scope = mapping

    def __getitem__(self, key: str):
        value = self.scope[key]
        return self.expand(value) if isinstance(value, str) else value

    def __contains__(self, key: str):
        return key in self.scope

    def get(self, key: str, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def expand(self, s: str) -> str:
        return s.format_map(self)

def ndget(d: Mapping[T, Any], keys: Iterable[T], default: Any = None) -> Any:
    """Get from nested dictionaries."""
    t: Any = d
    try:
        for k in keys:
            if k not in t:
                return default
            t = t[k]
        return t
    except (KeyError, TypeError):
        return default

def ndupdate(d: MutableMapping, s: Mapping):
    """Update nested dictionaries."""
    for k, v in s.items():
        if k not in d:
            d[k] = v
            continue
        if isinstance(d[k], MutableMapping) and isinstance(v, Mapping):
            ndupdate(d[k], v)
            continue
        if isinstance(d[k], MutableSequence) and isinstance(v, Sequence):
            d[k] += v
            continue
        if isinstance(d[k], MutableSet) and isinstance(v, Set):
            d[k] |= v
            continue
        if type(d[k]) == type(v):
            d[k] = v
            continue
        raise TypeError(k, d[k], v)
    return d

def shell_escape(s: str, interpolatable: bool = True) -> str:
    if not interpolatable:
        return shlex.quote(s)
    r = ['"']
    for c in s:
        if c == '"' or c == '\\':
            r.append('\\')
        r.append(c)
    r.append('"')
    return ''.join(r)

def toml_escape(s: str) -> str:
    r = []
    for c in s:
        a = ord(c)
        if a == 34 or a == 92 or a < 32:
            c = f'\\u{a:04X}'
        r.append(c)
    return ''.join(r)

def xdg_dir(name: str, default_dir: str) -> Path:
    evar = f'XDG_{name}_HOME'
    if evar in os.environ:
        xdg_home = Path(os.environ[evar])
        if not xdg_home.is_dir():
            xdg_home.mkdir(parents=True)
        return xdg_home
    default = Path.home() / default_dir
    if not default.is_dir():
        default.mkdir(parents=True)
    return default

class OriginStatus(Enum):
    # TODO
    UNCHANGED = 0
    ERROR = 1
    UNKNOWN = 2
    UPGRADABLE = 3
    DIRTY = 4

class Origin(ABC):
    """Base class for package origin methods."""
    subclass: dict[str, Type[Self]] = {}

    def __init__(self, name: str, remote: str | Path, local: Path):
        self.name = name
        self.remote = remote
        self.local = local

    def __init_subclass__(cls, name: str):
        cls.subclass[name] = cls

    def refresh(self) -> bool:
        return self.update() if self.local.exists() else self.clone()

    def update(self) -> bool:
        return self._update() if self._check() else False

    def clone(self) -> bool:
        return self._clone() if self.check_local_is_available() else False

    def status(self) -> OriginStatus:
        return self._status() if self._check() else OriginStatus.ERROR

    def bootstrap(self) -> bool:
        print(f'mkdir -p {shell_escape(str(self.local.parent))}')
        return self._bootstrap()

    def check_local_is_dir(self) -> bool:
        if not self.local.exists():
            error(f'{self.name}: {self.local} does not exist.')
            return False
        if not self.local.is_dir():
            error(f'{self.name}: {self.local} is not a directory.')
            return False
        return True

    def check_local_is_available(self) -> bool:
        if self.local.exists():
            error(f'{self.name}: {self.local} already exists.')
            return False
        if not self.local.parent.is_dir():
            try:
                self.local.parent.mkdir(parents=True)
            except OSError as e:
                error(f'{self.name}: {self.local} could not be created: {e}.')
                return False
        return True

    @abstractmethod
    def _check(self) -> bool:
        return False

    @abstractmethod
    def _clone(self) -> bool:
        pass

    @abstractmethod
    def _update(self) -> bool:
        pass

    @abstractmethod
    def _status(self) -> OriginStatus:
        return OriginStatus.UNKNOWN

    @abstractmethod
    def _bootstrap(self) -> bool:
        pass

    @classmethod
    def vcs_by_name(cls, name: str):
        return cls.subclass[name]

    def _runp(self, command: Sequence[str],
              **kwargs) -> subprocess.CompletedProcess:
        return subprocess.run(
            command, check=True, text=True, capture_output=True, **kwargs)

    def _run(self, command: Sequence[str], **kwargs) -> bool:
        p = self._runp(command, **kwargs)
        if p.stderr or p.stdout:
            print(f'{self.name}:')
            if p.stderr:
                print(p.stderr)
            if p.stdout:
                print(p.stdout)
        return p.returncode == 0

class GitOrigin(Origin, name='git'):
    """A package under Git version control with a remote master."""

    def _check(self) -> bool:
        if not self.check_local_is_dir():
            return False
        if not self.local.joinpath('.git').is_dir():
            error(f'{self.name}: {self.local} is not a Git repository.')
            return False
        # TODO: check that the primary remote matches `self.src`.
        return True

    def _bootstrap(self) -> bool:
        local = shell_escape(str(self.local))
        print(f'if test -d {local}')
        print(f'then (cd {local} && git pull --rebase)')
        print(f'else git clone {shell_escape(str(self.remote))} {local}')
        print('fi')
        return True

    def _clone(self) -> bool:
        return self._run(['git', 'clone', str(self.remote), str(self.local)])

    def _update(self) -> bool:
        return self._run(['git', 'pull', '--rebase'], cwd=self.local)

    def _status(self) -> OriginStatus:
        # TODO return status
        self._run(['git', 'status', '--short'], cwd=self.local)
        return OriginStatus.UNKNOWN

class MercurialOrigin(Origin, name='hg'):
    """A package under Mercurial version control with a remote master."""

    def _check(self) -> bool:
        if not self.check_local_is_dir():
            return False
        if not self.local.joinpath('.hg').is_dir():
            error(f'{self.name}: {self.local} is not a Mercurial repository.')
            return False
        # TODO: check that the primary remote matches `self.src`.
        return True

    def _bootstrap(self) -> bool:
        local = shell_escape(str(self.local))
        print(f'if test -d {local}')
        print(f'then (cd {local} && hg pull -u)')
        print(f'else hg clone {shell_escape(str(self.remote))} {local}')
        print('fi')
        return True

    def _clone(self):
        return self._run(['hg', 'clone', str(self.remote), str(self.local)])

    def _update(self):
        return self._run(['hg', 'pull', '-u'], cwd=self.local)

    def _status(self):
        # TODO return status
        self._run(['hg', 'status'], cwd=self.local)
        return OriginStatus.UNKNOWN

class SymlinkOrigin(Origin, name='ln'):
    """A package symbolically linked to a master local directory."""

    def __init__(self, name: str, remote: str | Path, local: Path):
        super().__init__(name, remote, local)
        self.src: Path = Path(remote)

    def _check(self) -> bool:
        if not self.check_local_is_dir():
            return False
        if not self.local.is_symlink():
            error(f'{self.name}: {self.local} is not a symbolic link.')
            return False
        if self.local.resolve() != self.src.resolve():
            error(f'{self.name}: {self.local} does not point to {self.src}')
            return False
        return True

    def _bootstrap(self) -> bool:
        local = shell_escape(str(self.local))
        print(f'test -d {local} ||'
              f' ln -s {shell_escape(str(self.remote))} {local}')
        return True

    def _clone(self):
        self.src.symlink_to(self.local)

    def _update(self):
        pass

    def _status(self) -> OriginStatus:
        return OriginStatus.UNCHANGED

class Package:

    def __init__(self, name: str, origin: Origin, info: Expander):
        self.name = name
        self.origin = origin
        self.info = info

def read_toml(files: Iterable) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for file in files:
        if isinstance(file, (str, Path)):
            with open(file, 'rb') as f:
                a = tomllib.load(f)
        else:
            a = tomllib.load(file)
        ndupdate(data, a)
    return data

def read_inputs(files: Iterable):
    """Given filenames, read them all."""
    config = read_toml(files)

    env = dict(os.environ)
    glo: dict[str, Any] = config.get('global', {})
    glo['CONFIG_HOME'] = str(xdg_dir('CONFIG', '.config'))
    glo['DATA_HOME'] = str(xdg_dir('DATA', '.local/share'))
    glo['STATE_HOME'] = str(xdg_dir('STATE', '.local/state'))
    glo['CACHE_HOME'] = str(xdg_dir('CACHE', '.cache'))
    gcm = ChainMap({'global': glo, 'env': env}, glo, env)

    packages: dict[str, Package] = {}

    for key, properties in config.get('package', {}).items():
        properties['key'] = key
        name = properties.setdefault('name', key)

        if 'template' in properties:
            template = ndget(config, ['template', properties['template']], {})
        else:
            template = {}

        cm = ChainMap({'package': properties}, properties, template, gcm)
        info = Expander(cm)

        load = info.get('load', True)
        if isinstance(load, (bool, list)):
            pass
        elif isinstance(load, str):
            load = [load]
        else:
            raise TypeError(load)
        properties['load'] = load

        d = info.get('dst')
        if d:
            dst = Path(d)
        else:
            dst = Path.cwd() / name
            properties['dst'] = str(dst)

        src = info.get('src')
        if not isinstance(src, str):
            error(f'{name}: missing ‘src’ key.')
            continue

        vcs = info.get('vcs')
        if not isinstance(vcs, str):
            if src.endswith('.git'):
                properties['vcs'] = 'git'
                vcs = 'git'
            else:
                error(f'{name}: missing ‘vcs’ key.')
                continue

        try:
            vcls = Origin.vcs_by_name(vcs)
        except KeyError:
            error(f'{name}: {vcs} is not a known source type.')
            continue

        origin = vcls(name, src, dst)
        packages[key] = Package(name, origin, info)

    return packages, gcm, config

def build_output(packages: Mapping[str, Package], ginfo: Expander,
                 config: dict[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    gkeys = (['CONFIG_HOME', 'DATA_HOME', 'STATE_HOME', 'CACHE_HOME']
             + ndget(config, ['output', 'global', 'keys'], []))
    for k in gkeys:
        output[k] = ginfo.get(k)
    for k, template in ndget(config, ['output', 'global', 'items'], {}).items():
        output[k] = template.format_map(ginfo)
    pkeys = (['name', 'src', 'dst', 'vcs', 'load']
             + ndget(config, ['output', 'package', 'keys'], []))
    pitems = ndget(config, ['output', 'package', 'items'], {})
    output['package'] = {}
    for key, package in packages.items():
        package_output: dict[str, Any] = {}
        for k in pkeys:
            package_output[k] = package.info.get(k)
        for k, template in pitems.items():
            package_output[k] = template.format_map(package.info)
        output['package'][key] = package_output
    return output

def build_list(variant: str, packages: Mapping[str, Package], ginfo: Expander,
               config: dict[str, Any]) -> str:
    out: list[str] = []
    for k in ndget(config, ['list', variant, 'global', 'keys'], []):
        out.append(str(ginfo.get(k)))
    for k, template in ndget(config, ['list', variant, 'global', 'items'],
                             {}).items():
        out.append(template.format_map(ginfo))
    for package in packages.values():
        load = package.info.get('load')
        if isinstance(load, list):
            load = variant in load
        if load:
            for k in ndget(config, ['list', variant, 'package', 'keys'], []):
                out.append(str(package.info.get(k)))
            for k, template in ndget(config,
                                     ['list', variant, 'package', 'items'],
                                     {}).items():
                out.append(template.format_map(package.info))
    out.append('')
    return '\n'.join(out)

def main(argv: Sequence[str] | None = None):
    if argv is None:
        argv = sys.argv  # pragma: no cover
    global SELF
    SELF = Path(argv[0]).stem
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'files', metavar='TOML', type=str, nargs='+', help='input file name(s)')
    parser.add_argument(
        '--all',
        '-a',
        action='store_true',
        default=False,
        help='Also perform repository operations on un-loaded packages')
    parser.add_argument(
        '--define',
        '-D',
        metavar=('NAME', 'VALUE'),
        nargs=2,
        action='append',
        help='Define a value, overriding TOML files')
    parser.add_argument(
        '--package',
        '-p',
        metavar='NAME',
        type=str,
        action='append',
        help='Limit operations to named packages')
    parser.add_argument(
        '--bootstrap',
        '-b',
        action='store_true',
        default=False,
        help='Print shell commands to get packages')
    parser.add_argument(
        '--refresh',
        '-r',
        action='store_true',
        default=False,
        help='Clone or update packages')
    parser.add_argument(
        '--status',
        '-s',
        action='store_true',
        default=False,
        help='Report status of packages')
    parser.add_argument(
        '--json',
        '-j',
        action='store_true',
        default=False,
        help='Print package information as JSON')
    parser.add_argument(
        '--list',
        '-l',
        action='store_true',
        default=False,
        help='Write package information as configured list files')
    parser.add_argument(
        '--list-type',
        '-L',
        metavar='NAME',
        type=str,
        action='append',
        help='Limit list writing to named variants')
    args = parser.parse_args(argv[1 :])

    inputs = list(args.files)
    if args.define:
        for k, v in args.define:
            s = f'{k} = "{toml_escape(v)}"'
            inputs.append(io.BytesIO(bytes(s, encoding='utf-8')))

    packages, gcm, config = read_inputs(inputs)

    if args.package:
        selected = {}
        for key in args.package:
            if key in packages:
                selected[key] = packages[key]
            else:
                error(f'{key}: not a configured package.')
        packages = selected

    for key, package in packages.items():
        if args.all or package.info.get('load', True):
            if args.bootstrap:
                package.origin.bootstrap()
            if args.refresh:
                package.origin.refresh()
            if args.status:
                package.origin.status()

    ginfo = Expander(gcm)

    if args.json:
        output = build_output(packages, ginfo, config)
        json.dump(output, sys.stdout, indent=1)

    if args.list or args.list_type:
        variants = set(ndget(config, ['list']).keys())
        if args.list_type:
            variants &= set(args.list_type)
        for v in variants:
            file = ndget(config, ['list', v, 'file'])
            if file is None:
                error(f"Missing file for list type ‘{v}’")
                continue
            filename = Path(ginfo.expand(file))
            if not filename.parent.exists():
                filename.parent.mkdir(parents=True)
            if filename.exists():
                b = filename.with_suffix('.bak')
                if b.exists():
                    b.unlink()
                filename.rename(b)
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(build_list(v, packages, ginfo, config))

    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv))  # pragma: no cover
