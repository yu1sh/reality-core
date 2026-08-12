#!/usr/bin/env python3
"""Validate the canonical, dependency-free CycloneDX runtime SBOM."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable


MAX_SBOM_BYTES = 512 * 1024
MAX_DEPTH = 16
MAX_STRING_BYTES = 16 * 1024
POSIX_ROOT_NAMES = ("home", "Users", "tmp", "var", "opt", "root", "workspace", "mnt")
POSIX_ABSOLUTE_RE = re.compile(
    rb"(?<![A-Za-z0-9_])/(?:" + b"|".join(name.encode() for name in POSIX_ROOT_NAMES) + rb")(?:/|$)"
)
WINDOWS_ABSOLUTE_RE = re.compile(rb"(?<![A-Za-z0-9_])[A-Za-z]:[\\/]")
TIMESTAMP_VALUE_RE = re.compile(
    r"\b20[0-9]{2}-[0-9]{2}-[0-9]{2}(?:[T ][0-9]{2}:[0-9]{2}:[0-9]{2})?\b"
)


class ValidationError(ValueError):
    pass


def _walk(value: Any, key: str = "", depth: int = 0) -> Iterable[tuple[str, Any]]:
    if depth > MAX_DEPTH:
        raise ValidationError("SBOM nesting is too deep")
    yield key, value
    if isinstance(value, dict):
        for child_key, child_value in value.items():
            yield from _walk(child_value, str(child_key), depth + 1)
    elif isinstance(value, list):
        for child_value in value:
            yield from _walk(child_value, key, depth + 1)


def _reject_paths_and_timestamps(document: dict[str, Any]) -> None:
    for key, value in _walk(document):
        if key.lower() in {"timestamp", "created", "createdat", "generatedat", "serialnumber"}:
            raise ValidationError("SBOM must not contain timestamps or serial numbers")
        if isinstance(value, str):
            if len(value.encode("utf-8")) > MAX_STRING_BYTES:
                raise ValidationError("SBOM string is too large")
            encoded = value.encode("utf-8")
            if POSIX_ABSOLUTE_RE.search(encoded) or WINDOWS_ABSOLUTE_RE.search(encoded):
                raise ValidationError("SBOM must not contain local absolute paths")
            if TIMESTAMP_VALUE_RE.search(value):
                raise ValidationError("SBOM must not contain generated timestamps")


def _root_reference() -> str:
    return "pkg:maven/io.github.yu1sh.reality/reality-core@0.1.0-SNAPSHOT"


def validate_document(document: dict[str, Any]) -> None:
    expected_top_level = [
        "bomFormat",
        "specVersion",
        "version",
        "metadata",
        "components",
        "dependencies",
    ]
    if list(document) != expected_top_level:
        raise ValidationError("SBOM top-level keys are not canonical")
    if document.get("bomFormat") != "CycloneDX" or document.get("specVersion") != "1.5":
        raise ValidationError("SBOM format/specification is incorrect")
    if document.get("version") != 1:
        raise ValidationError("SBOM version must be deterministic 1")

    metadata = document.get("metadata")
    if not isinstance(metadata, dict) or list(metadata) != ["component"]:
        raise ValidationError("SBOM metadata must contain only the root component")
    root = metadata["component"]
    if not isinstance(root, dict):
        raise ValidationError("SBOM root component is missing")
    required_root_keys = ["type", "group", "name", "version", "bom-ref", "purl"]
    if list(root) != required_root_keys:
        raise ValidationError("SBOM root component is not canonical")
    expected_root = {
        "type": "library",
        "group": "io.github.yu1sh.reality",
        "name": "reality-core",
        "version": "0.1.0-SNAPSHOT",
        "bom-ref": _root_reference(),
        "purl": _root_reference(),
    }
    if root != expected_root:
        raise ValidationError("SBOM root component is not the reviewed component")

    components = document.get("components")
    if components != []:
        raise ValidationError("runtime SBOM must contain zero dependency components")

    dependencies = document.get("dependencies")
    if dependencies != [{"ref": _root_reference(), "dependsOn": []}]:
        raise ValidationError("SBOM dependency relationship is not canonical")

    serialized = json.dumps(document, sort_keys=True).lower()
    if any(term in serialized for term in ("junit", "testimplementation", "test-runtime", "testscope")):
        raise ValidationError("test-scope content entered the runtime SBOM")
    _reject_paths_and_timestamps(document)


def _object_without_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValidationError("SBOM contains duplicate JSON keys")
        result[key] = value
    return result


def _reject_constant(value: str) -> Any:
    raise ValidationError(f"SBOM contains non-standard JSON constant {value}")


def validate_file(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_SBOM_BYTES:
        raise ValidationError("SBOM file is missing, is a symlink, or exceeds the bounded limit")
    data = path.read_bytes()
    if b"\0" in data or data.startswith(b"\xef\xbb\xbf"):
        raise ValidationError("SBOM must be UTF-8 without BOM or NUL bytes")
    try:
        document = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_object_without_duplicate_keys,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValidationError("SBOM is not valid UTF-8 JSON") from error
    if not isinstance(document, dict):
        raise ValidationError("SBOM root must be a JSON object")
    validate_document(document)
    return document


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sbom", type=Path)
    args = parser.parse_args(argv)
    try:
        document = validate_file(args.sbom)
    except (OSError, ValidationError, ValueError) as error:
        print("runtime_sbom_invalid: " + str(error), file=sys.stderr)
        return 1
    print("runtime_sbom_valid components=" + str(len(document["components"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
