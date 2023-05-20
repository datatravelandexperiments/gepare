# SPDX-License-Identifier: MIT
"""Unit test helpers"""

import io
import subprocess

from collections.abc import Mapping


def make_mapped(d: Mapping, default=None):
    record = []

    def fake(name, *_a, **_k):
        s = str(name)
        record.append(s)
        return d.get(s, default)

    return fake, record

def fake_mapped(d: Mapping, default=None):
    return make_mapped(d, default)[0]

def make_none():
    record = []

    def fake(*args):
        record.append(args)

    return fake, record

def make_run():
    record: list[subprocess.CompletedProcess] = []

    def fake(args, **_):
        cp = subprocess.CompletedProcess(args, 0, '', '')
        record.append(cp)
        return cp

    return fake, record

def stringio() -> io.StringIO:
    s = io.StringIO()
    s.close = lambda: None
    return s
