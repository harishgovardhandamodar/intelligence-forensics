"""Tiny YAML-subset reader for settings.yaml (stdlib only).

Supports exactly what settings.yaml uses: top-level `key: value` scalars
(ints/floats/strings) and one-level `key:` sections holding `- item` lists.
Anything fancier raises — config stays boring on purpose.
"""
from __future__ import annotations


def _scalar(raw: str):
    raw = raw.strip()
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        pass
    return raw


def load_settings(path: str) -> dict:
    out: dict = {}
    current: str | None = None
    with open(path, encoding="utf-8") as f:
        for line in f:
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            if line.startswith((" ", "\t")):
                text = line.strip()
                if text.startswith("- ") and current:
                    out[current].append(_scalar(text[2:]))
                continue
            if ":" not in line:
                raise ValueError(f"bad settings line: {line!r}")
            key, _, val = line.partition(":")
            key, val = key.strip(), val.strip()
            if val == "":
                current = key
                out[key] = []
            else:
                current = None
                out[key] = _scalar(val)
    return out
