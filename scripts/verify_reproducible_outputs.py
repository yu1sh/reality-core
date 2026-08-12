#!/usr/bin/env python3
"""Validate and compare the reviewed library artifacts across clean builds."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path
from typing import Any


MAX_STATE_BYTES = 64 * 1024
MAX_ARTIFACT_BYTES = 64 * 1024 * 1024
MAX_ARCHIVE_ENTRIES = 4096
MAX_ARCHIVE_TOTAL_BYTES = 128 * 1024 * 1024
TIMESTAMP_RE = re.compile(rb"\b20[0-9]{2}-[0-9]{2}-[0-9]{2}[T ][0-9]{2}:[0-9]{2}:[0-9]{2}\b")
POSIX_PATH_RE = re.compile(
    rb"(?<![A-Za-z0-9_])/(?:bin|boot|dev|etc|home|lib|lib32|lib64|media|mnt|opt|proc|root|run|sbin|srv|sys|tmp|usr|var|Users|workspace)(?:/|$)"
)
WINDOWS_PATH_RE = re.compile(rb"(?<![A-Za-z0-9_])[A-Za-z]:[\\/]")
PRIVATE_KEY_RE = re.compile(rb"-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY-----")
CONTROL_BYTE_RE = re.compile(rb"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

ARTIFACTS = (
    "build/libs/reality-core-0.1.0-SNAPSHOT.jar",
    "build/libs/reality-core-0.1.0-SNAPSHOT-sources.jar",
    "build/libs/reality-core-0.1.0-SNAPSHOT-javadoc.jar",
    "staging/reality-core.pom",
    "staging/reality-core.module",
)


class ArtifactError(ValueError):
    pass


def _canonical_zip_order(names: list[str]) -> list[str]:
    name_set = set(names)

    def children(prefix: str) -> tuple[list[str], list[str]]:
        directories: set[str] = set()
        files: set[str] = set()
        for name in names:
            if not name.startswith(prefix) or name == prefix:
                continue
            remainder = name[len(prefix) :]
            head, separator, _tail = remainder.partition("/")
            if separator:
                directories.add(prefix + head + "/")
            elif remainder:
                files.add(prefix + remainder)
        return sorted(directories), sorted(files)

    ordered: list[str] = []

    def visit(directory: str) -> None:
        directories, files = children(directory)
        for child in directories:
            ordered.append(child)
            visit(child)
        ordered.extend(files)

    if "META-INF/" in name_set:
        ordered.append("META-INF/")
        visit("META-INF/")
    root_directories, root_files = children("")
    ordered.extend(root_files)
    for directory in root_directories:
        if directory == "META-INF/":
            continue
        ordered.append(directory)
        visit(directory)
    return ordered


def _bounded_bytes(path: Path) -> bytes:
    size = path.stat().st_size
    if size > MAX_ARTIFACT_BYTES:
        raise ArtifactError(f"artifact is larger than the bounded limit: {path}")
    data = path.read_bytes()
    if len(data) != size:
        raise ArtifactError(f"artifact changed while being read: {path}")
    return data


def _validate_content(data: bytes, label: str, *, allow_binary: bool = False) -> None:
    if CONTROL_BYTE_RE.search(data) and not allow_binary:
        raise ArtifactError(f"control byte in text publication metadata: {label}")
    if POSIX_PATH_RE.search(data) or WINDOWS_PATH_RE.search(data):
        raise ArtifactError(f"absolute local path in artifact: {label}")
    if PRIVATE_KEY_RE.search(data):
        raise ArtifactError(f"private-key marker in artifact: {label}")
    if TIMESTAMP_RE.search(data):
        raise ArtifactError(f"build timestamp in artifact: {label}")


def _validate_archive(path: Path) -> None:
    try:
        archive = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile) as error:
        raise ArtifactError(f"invalid reproducible archive: {path}") from error
    try:
        infos = archive.infolist()
        if not infos or len(infos) > MAX_ARCHIVE_ENTRIES:
            raise ArtifactError(f"archive entry count is outside the bounded range: {path}")
        names = [info.filename for info in infos]
        if names != _canonical_zip_order(names) or len(names) != len(set(names)):
            raise ArtifactError(f"archive entries are not unique and canonical: {path}")
        if any(
            not name
            or name.startswith(("/", "\\"))
            or "\\" in name
            or any(part in {"", ".", ".."} for part in (name.rstrip("/").split("/")))
            or "\0" in name
            for name in names
        ):
            raise ArtifactError(f"archive contains an unsafe entry name: {path}")
        timestamps = {info.date_time for info in infos}
        if len(timestamps) != 1 or next(iter(timestamps)) != (1980, 2, 1, 0, 0, 0):
            raise ArtifactError(f"archive entry timestamps are not the fixed Gradle value: {path}")
        total = 0
        for info in infos:
            total += info.file_size
            if total > MAX_ARCHIVE_TOTAL_BYTES:
                raise ArtifactError(f"archive contents exceed the bounded limit: {path}")
            data = archive.read(info)
            if len(data) != info.file_size:
                raise ArtifactError(f"archive entry changed while being read: {path}")
            _validate_content(data, info.filename, allow_binary=True)
    finally:
        archive.close()


def _hash(path: Path) -> str:
    return hashlib.sha256(_bounded_bytes(path)).hexdigest()


def collect_artifact_hashes(root: Path) -> dict[str, Any]:
    values: dict[str, str] = {}
    for relative in ARTIFACTS:
        if relative == "staging/reality-core.pom":
            path = _staged_file(root, "pom")
        elif relative == "staging/reality-core.module":
            path = _staged_file(root, "module")
        else:
            path = root / relative
        if path.is_symlink() or not path.is_file():
            raise ArtifactError(f"required artifact is missing or is a symlink: {relative}")
        data = _bounded_bytes(path)
        if relative.endswith((".jar",)):
            _validate_archive(path)
        else:
            _validate_content(data, relative)
        values[relative] = _hash(path)
    return {"schemaVersion": 1, "artifacts": values}


def _staged_file(root: Path, extension: str) -> Path:
    directory = root / "build/staging/repository/io/github/yu1sh/reality/reality-core/0.1.0-SNAPSHOT"
    candidates = sorted(
        path
        for path in directory.glob(f"reality-core-0.1.0-*.{extension}")
        if re.fullmatch(rf"reality-core-0\.1\.0-[0-9]{{8}}\.[0-9]{{6}}-[0-9]+\.{extension}", path.name)
    )
    if len(candidates) != 1:
        raise ArtifactError(f"expected one timestamped staged {extension} file")
    return candidates[0]


def _read_state(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ArtifactError("reproducibility state is missing or is a symlink")
    data = path.read_bytes()
    if len(data) > MAX_STATE_BYTES or b"\0" in data:
        raise ArtifactError("reproducibility state is too large or contains NUL")

    def no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ArtifactError("reproducibility state contains duplicate keys")
            result[key] = value
        return result

    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=no_duplicates)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ArtifactError("reproducibility state is not valid UTF-8 JSON") from error
    if not isinstance(value, dict) or value != {"schemaVersion": 1, "artifacts": dict(value.get("artifacts", {}))}:
        raise ArtifactError("reproducibility state has an unexpected shape")
    if list(value) != ["schemaVersion", "artifacts"] or list(value["artifacts"]) != list(ARTIFACTS):
        raise ArtifactError("reproducibility state is not canonical")
    if any(not isinstance(item, str) or not re.fullmatch(r"[0-9a-f]{64}", item) for item in value["artifacts"].values()):
        raise ArtifactError("reproducibility state contains an invalid SHA-256")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", type=Path)
    mode.add_argument("--compare", type=Path)
    args = parser.parse_args(argv)
    try:
        current = collect_artifact_hashes(args.repo_root.resolve(strict=True))
        if args.write is not None:
            args.write.parent.mkdir(parents=True, exist_ok=True)
            args.write.write_text(json.dumps(current, indent=2) + "\n", encoding="utf-8")
            print("reproducible_artifacts_recorded " + str(len(ARTIFACTS)))
        else:
            first = _read_state(args.compare)
            if first != current:
                raise ArtifactError("clean-build artifact hashes differ")
            print("reproducible_artifacts_match " + str(len(ARTIFACTS)))
    except (OSError, ArtifactError) as error:
        print(f"reproducible_artifacts_invalid: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
