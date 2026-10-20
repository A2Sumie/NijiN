# SPDX-License-Identifier: GPL-2.0-or-later
# SPDX-FileCopyrightText: 2026 the NijiN authors
"""The package authentication constant, read from local configuration.

It is a key-shaped literal and it does not belong in source. Lookup order:

  1. `$Z8_AUTH_APPEND`      hex string, direct value
  2. `$Z8_AUTH_CONFIG`      path to a JSON file carrying "auth_append"
  3. `auth_append.local.json` or `secrets/auth_append.local.json`, walking up from here

A build without the constant fails loudly instead of guessing: a wrong value changes the
outer SHA1 and every package would be refused, which is the safe direction.
"""
import json
import os
from pathlib import Path

ENV_VALUE = 'Z8_AUTH_APPEND'
ENV_CONFIG = 'Z8_AUTH_CONFIG'
CONFIG_NAME = 'auth_append.local.json'


def auth_append() -> bytes:
    raw = os.environ.get(ENV_VALUE)
    if raw:
        return bytes.fromhex(raw.strip())
    candidates = []
    named = os.environ.get(ENV_CONFIG)
    if named:
        candidates.append(Path(named))
    here = Path(__file__).resolve()
    for parent in (here.parent, *here.parents):
        candidates.append(parent / CONFIG_NAME)
        candidates.append(parent / 'secrets' / CONFIG_NAME)
    for candidate in candidates:
        if candidate.is_file():
            value = json.loads(candidate.read_text())['auth_append']
            out = bytes.fromhex(value)
            if len(out) != 8:
                raise ValueError('%s: auth_append must be 8 bytes' % candidate)
            return out
    raise ValueError('authentication constant is not configured: bring your own key — python3 z8auth.py setup --package /path/to/your/official.bin')
