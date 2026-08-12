#!/usr/bin/env python3
"""Run jdeps over the complete main output and require java.base only."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path


MAX_OUTPUT_BYTES = 64 * 1024
MAX_CLASS_FILES = 4096


class JdepsError(ValueError):
    pass


def _jdeps_path(java_home: Path) -> Path:
    name = "jdeps.exe" if os.name == "nt" else "jdeps"
    bin_directory = (java_home / "bin").resolve(strict=True)
    path = (java_home / "bin" / name).resolve(strict=True)
    if not path.is_file() or not os.access(path, os.X_OK) or path.parent != bin_directory:
        raise JdepsError("jdeps is not the exact JAVA_HOME/bin tool")
    return path


def verify_jdeps(classes_directory: Path, java_home: Path) -> str:
    if not classes_directory.is_dir() or classes_directory.is_symlink():
        raise JdepsError("main class directory is missing or is a symlink")
    class_files = sorted(classes_directory.rglob("*.class"))
    if not class_files or len(class_files) > MAX_CLASS_FILES:
        raise JdepsError("main class file count is outside the bounded range")
    if any(path.is_symlink() or not path.is_file() for path in class_files):
        raise JdepsError("main class output contains a symlink or non-file")
    command = [
        str(_jdeps_path(java_home)),
        "--multi-release",
        "17",
        "--print-module-deps",
        str(classes_directory),
    ]
    try:
        completed = subprocess.run(
            command,
            check=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise JdepsError("jdeps execution failed") from error
    if len(completed.stdout) > MAX_OUTPUT_BYTES or len(completed.stderr) > MAX_OUTPUT_BYTES:
        raise JdepsError("jdeps output exceeded the bounded limit")
    try:
        output = completed.stdout.decode("utf-8").strip()
        error_output = completed.stderr.decode("utf-8")
    except UnicodeDecodeError as error:
        raise JdepsError("jdeps output was not UTF-8") from error
    if error_output:
        raise JdepsError("jdeps wrote unexpected diagnostics")
    if output != "java.base":
        raise JdepsError(f"expected java.base only, got {output!r}")
    return output


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("classes_directory", type=Path)
    parser.add_argument("--java-home", type=Path)
    args = parser.parse_args(argv)
    try:
        java_home_value = args.java_home or os.environ.get("JAVA_HOME")
        if not java_home_value:
            raise JdepsError("JAVA_HOME or --java-home is required")
        output = verify_jdeps(args.classes_directory, Path(java_home_value).resolve(strict=True))
    except (OSError, JdepsError) as error:
        print(f"jdeps_invalid: {error}", file=sys.stderr)
        return 1
    print(f"jdeps_valid modules={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
