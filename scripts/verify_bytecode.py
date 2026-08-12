#!/usr/bin/env python3
"""Verify every main class file has the reviewed Java class-file major version."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


MAX_CLASS_FILES = 4096
MAX_CLASS_BYTES = 64 * 1024 * 1024
CLASS_HEADER_BYTES = 8


class BytecodeError(ValueError):
    pass


def verify_classes(classes_directory: Path, expected_major: int) -> tuple[int, int]:
    if expected_major != 61:
        raise BytecodeError("only Java 17 class major 61 is approved")
    if not classes_directory.is_dir() or classes_directory.is_symlink():
        raise BytecodeError("main class directory is missing or is a symlink")
    paths = sorted(classes_directory.rglob("*.class"))
    if not paths or len(paths) > MAX_CLASS_FILES:
        raise BytecodeError("main class file count is outside the bounded range")
    total_bytes = 0
    for path in paths:
        if path.is_symlink() or not path.is_file():
            raise BytecodeError("main classes must not contain symlinks or non-files")
        size = path.stat().st_size
        total_bytes += size
        if total_bytes > MAX_CLASS_BYTES:
            raise BytecodeError("main class byte size exceeded the bounded limit")
        data = path.read_bytes()
        if len(data) < CLASS_HEADER_BYTES or data[:4] != b"\xca\xfe\xba\xbe":
            raise BytecodeError(f"{path} is not a valid Java class file")
        major = int.from_bytes(data[6:8], "big")
        if major != expected_major:
            raise BytecodeError(f"{path} has class major {major}, expected {expected_major}")
    return len(paths), total_bytes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("classes_directory", type=Path)
    parser.add_argument("--expected-major", type=int, required=True)
    args = parser.parse_args(argv)
    try:
        count, total_bytes = verify_classes(args.classes_directory, args.expected_major)
    except (OSError, BytecodeError) as error:
        print(f"bytecode_invalid: {error}", file=sys.stderr)
        return 1
    print(f"bytecode_valid classes={count} major=61 bytes={total_bytes}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
