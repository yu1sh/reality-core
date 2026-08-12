#!/usr/bin/env python3
"""Compare the deterministic runtime SBOM across clean Gradle executions."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


MAX_SBOM_BYTES = 512 * 1024
EXPECTED_RELATIVE_PATH = "build/reports/sbom/reality-core-runtime-sbom.json"


class SbomReproducibilityError(ValueError):
    pass


def _digest(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise SbomReproducibilityError("SBOM is missing or is a symlink")
    if path.stat().st_size > MAX_SBOM_BYTES:
        raise SbomReproducibilityError("SBOM exceeds the bounded size")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_state(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise SbomReproducibilityError("SBOM state is missing or is a symlink")
    data = path.read_bytes()
    if len(data) > 16 * 1024 or b"\0" in data:
        raise SbomReproducibilityError("SBOM state is too large or contains NUL")

    def no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise SbomReproducibilityError("SBOM state contains duplicate keys")
            result[key] = value
        return result

    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=no_duplicates)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SbomReproducibilityError("SBOM state is not valid JSON") from error
    if not isinstance(value, dict) or list(value) != ["schemaVersion", "sha256"]:
        raise SbomReproducibilityError("SBOM state shape is not canonical")
    if value["schemaVersion"] != 1 or not isinstance(value["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", value["sha256"]):
        raise SbomReproducibilityError("SBOM state is not canonical")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--sbom", type=Path, default=Path(EXPECTED_RELATIVE_PATH))
    state = parser.add_mutually_exclusive_group(required=True)
    state.add_argument("--write", type=Path)
    state.add_argument("--compare", type=Path)
    args = parser.parse_args(argv)
    try:
        root = args.repo_root.resolve(strict=True)
        digest = _digest(root / args.sbom)
        current = {"schemaVersion": 1, "sha256": digest}
        if args.write is not None:
            args.write.parent.mkdir(parents=True, exist_ok=True)
            args.write.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")
            print(f"reproducible_sbom_recorded sha256={digest}")
        else:
            if _read_state(args.compare) != current:
                raise SbomReproducibilityError("clean-build SBOM hashes differ")
            print(f"reproducible_sbom_match sha256={digest}")
    except (OSError, SbomReproducibilityError) as error:
        print(f"reproducible_sbom_invalid: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
