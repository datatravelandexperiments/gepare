# SPDX-License-Identifier: MIT
"""Unit test helpers."""

import io
import subprocess

from collections.abc import Callable, Mapping
from typing import Any

def make_mapped(d: Mapping,
                default: Any | None = None) -> tuple[Callable, list]:
    record = []

    def fake(name: object, *_a, **_k) -> Any | None:
        s = str(name)
        record.append(s)
        return d.get(s, default)

    return fake, record

def fake_mapped(d: Mapping, default: Any | None = None) -> Callable:
    return make_mapped(d, default)[0]

def make_none() -> tuple[Callable, list]:
    record = []

    def fake(*args) -> None:
        record.append(args)

    return fake, record

def make_run() -> tuple[Callable, list[subprocess.CompletedProcess]]:
    record: list[subprocess.CompletedProcess] = []

    def fake(args: list[str], **_) -> subprocess.CompletedProcess:
        cp = subprocess.CompletedProcess(args, 0, '', '')
        record.append(cp)
        return cp

    return fake, record

def stringio() -> io.StringIO:
    s = io.StringIO()
    s.close = lambda: None
    return s
