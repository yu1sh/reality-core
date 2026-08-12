#!/usr/bin/env python3
"""Fail closed unless the reviewed Java toolchain and archive are in use."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any


MAX_MANIFEST_BYTES = 32 * 1024
MAX_COMMAND_OUTPUT_BYTES = 64 * 1024
MAX_ARCHIVE_BYTES = 512 * 1024 * 1024
DOWNLOAD_TIMEOUT_SECONDS = 30
DOWNLOAD_ATTEMPTS = 2
EXPECTED_JAVA_VERSION = "17.0.20"
EXPECTED_JAVA_RUNTIME_VERSION = "17.0.20+8"
EXPECTED_JAVA_VENDOR = "Eclipse Adoptium"
EXPECTED_ARCHIVE_SHA256 = "be7668bc030d578b83d6d5ef9221d6d6729bbbca8cf94a7d52e16ac68b5a5a35"
EXPECTED_MANIFEST_SHA256 = "afa1849495d444be4271e97977097790d432bede4e2d3f26ba642a2cfe1c288d"
EXPECTED_ARCHIVE_URL = (
    "https://github.com/adoptium/temurin17-binaries/releases/download/"
    "jdk-17.0.20%2B8/OpenJDK17U-jdk_x64_linux_hotspot_17.0.20_8.tar.gz"
)
EXPECTED_HEAD_RE = re.compile(r"[0-9a-f]{40}\Z")


class VerificationError(ValueError):
    """An input or runtime value did not meet the reviewed policy."""


def _read_bounded(path: Path, limit: int) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise VerificationError(f"input is missing or is a symlink: {path}")
    try:
        size = path.stat().st_size
    except OSError as error:
        raise VerificationError(f"cannot stat {path}") from error
    if size > limit:
        raise VerificationError(f"input is larger than the {limit}-byte limit")
    try:
        data = path.read_bytes()
    except OSError as error:
        raise VerificationError(f"cannot read {path}") from error
    if len(data) != size:
        raise VerificationError("input changed while it was being read")
    return data


def _object_without_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise VerificationError("JSON contains duplicate object keys")
        result[key] = value
    return result


def _read_manifest(path: Path) -> dict[str, Any]:
    data = _read_bounded(path, MAX_MANIFEST_BYTES)
    if hashlib.sha256(data).hexdigest() != EXPECTED_MANIFEST_SHA256:
        raise VerificationError("toolchain manifest bytes do not match the reviewed digest")
    if data.startswith(b"\xef\xbb\xbf") or b"\0" in data:
        raise VerificationError("manifest must be UTF-8 without BOM or NUL bytes")
    try:
        text = data.decode("utf-8")
        document = json.loads(text, object_pairs_hook=_object_without_duplicate_keys)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise VerificationError("manifest is not valid UTF-8 JSON") from error
    if not isinstance(document, dict):
        raise VerificationError("manifest root must be an object")
    if list(document) != ["schemaVersion", "java", "gradle"]:
        raise VerificationError("manifest top-level keys are not canonical")
    if not isinstance(document.get("java"), dict) or list(document["java"]) != [
        "distribution",
        "vendor",
        "version",
        "release",
        "classMajor",
        "archive",
    ]:
        raise VerificationError("manifest Java keys are not canonical")
    if not isinstance(document["java"].get("archive"), dict) or list(document["java"]["archive"]) != ["url", "sha256"]:
        raise VerificationError("manifest archive keys are not canonical")
    if not isinstance(document.get("gradle"), dict) or list(document["gradle"]) != ["version"]:
        raise VerificationError("manifest Gradle keys are not canonical")
    expected = {
        "schemaVersion": 1,
        "java": {
            "distribution": "temurin",
            "vendor": EXPECTED_JAVA_VENDOR,
            "version": EXPECTED_JAVA_RUNTIME_VERSION,
            "release": 17,
            "classMajor": 61,
            "archive": {
                "url": EXPECTED_ARCHIVE_URL,
                "sha256": EXPECTED_ARCHIVE_SHA256,
            },
        },
        "gradle": {"version": "9.3.0"},
    }
    if document != expected:
        raise VerificationError("toolchain manifest differs from the reviewed exact values")
    return document


def _run(command: list[str], *, cwd: Path, timeout: int = 15) -> str:
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            check=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            text=False,
        )
    except (OSError, subprocess.SubprocessError) as error:
        raise VerificationError(f"failed to execute {' '.join(command)}") from error
    output = completed.stdout
    if len(output) > MAX_COMMAND_OUTPUT_BYTES:
        raise VerificationError(f"output from {command[0]} exceeded the bounded limit")
    try:
        return output.decode("utf-8")
    except UnicodeDecodeError as error:
        raise VerificationError(f"{command[0]} output was not UTF-8") from error


def _tool_path(java_home: Path, name: str) -> Path:
    executable = name + (".exe" if os.name == "nt" else "")
    bin_directory = (java_home / "bin").resolve(strict=True)
    path = java_home / "bin" / executable
    if not path.is_file() or not os.access(path, os.X_OK):
        raise VerificationError(f"missing executable {name} in JAVA_HOME/bin")
    resolved = path.resolve(strict=True)
    if resolved.parent != bin_directory:
        raise VerificationError(f"{name} resolves outside the exact JAVA_HOME/bin")
    return resolved


def _properties(output: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in output.splitlines():
        match = re.fullmatch(r"\s+([A-Za-z0-9_.]+) = (.*)", line)
        if match:
            key, value = match.groups()
            if key in values:
                raise VerificationError(f"duplicate Java property {key}")
            values[key] = value
    return values


def _verify_runtime(java_home: Path, repo_root: Path) -> tuple[Path, dict[str, str]]:
    tools = {name: _tool_path(java_home, name) for name in ("java", "javac", "javadoc", "jdeps")}
    output = _run([str(tools["java"]), "-XshowSettings:properties", "-version"], cwd=repo_root)
    properties = _properties(output)
    required = {
        "java.home": str(java_home),
        "java.vendor": EXPECTED_JAVA_VENDOR,
        "java.version": EXPECTED_JAVA_VERSION,
        "java.runtime.version": EXPECTED_JAVA_RUNTIME_VERSION,
    }
    for key, expected in required.items():
        if properties.get(key) != expected:
            raise VerificationError(f"{key} is not the reviewed exact value")
    if Path(properties["java.home"]).resolve() != java_home:
        raise VerificationError("java.home is not the declared JAVA_HOME")

    expected_outputs = {
        "javac": f"javac {EXPECTED_JAVA_VERSION}",
        "javadoc": f"javadoc {EXPECTED_JAVA_VERSION}",
        "jdeps": EXPECTED_JAVA_VERSION,
    }
    for name, expected in expected_outputs.items():
        actual = _run([str(tools[name]), "--version"], cwd=repo_root).strip()
        if actual != expected:
            raise VerificationError(f"{name} is not the reviewed exact version")
    return tools["java"], properties


def _sha256(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise VerificationError("JDK archive is missing or is a symlink")
    try:
        size = path.stat().st_size
    except OSError as error:
        raise VerificationError("cannot stat JDK archive") from error
    if size <= 0 or size > MAX_ARCHIVE_BYTES:
        raise VerificationError("JDK archive size is outside the bounded range")
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as error:
        raise VerificationError("cannot read JDK archive") from error
    return digest.hexdigest()


def _verify_archive(path: Path) -> None:
    if _sha256(path) != EXPECTED_ARCHIVE_SHA256:
        raise VerificationError("JDK archive SHA-256 does not match the manifest")


def _download_and_verify() -> None:
    request = urllib.request.Request(
        EXPECTED_ARCHIVE_URL,
        headers={"User-Agent": "reality-core-toolchain-verifier/1"},
        method="GET",
    )
    last_error: BaseException | None = None
    for _attempt in range(DOWNLOAD_ATTEMPTS):
        try:
            with urllib.request.urlopen(request, timeout=DOWNLOAD_TIMEOUT_SECONDS) as response:
                if response.status != 200:
                    raise VerificationError("JDK archive download did not return HTTP 200")
                content_length = response.headers.get("Content-Length")
                if content_length is not None:
                    try:
                        declared_size = int(content_length)
                    except ValueError as error:
                        raise VerificationError("JDK archive Content-Length is invalid") from error
                    if declared_size <= 0 or declared_size > MAX_ARCHIVE_BYTES:
                        raise VerificationError("JDK archive Content-Length is outside the limit")
                digest = hashlib.sha256()
                total = 0
                while True:
                    chunk = response.read(1024 * 1024)
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > MAX_ARCHIVE_BYTES:
                        raise VerificationError("JDK archive exceeded the bounded download limit")
                    digest.update(chunk)
                if total == 0 or digest.hexdigest() != EXPECTED_ARCHIVE_SHA256:
                    raise VerificationError("downloaded JDK archive SHA-256 is not exact")
                return
        except (OSError, urllib.error.URLError, VerificationError) as error:
            last_error = error
    raise VerificationError("unable to download and verify the exact JDK archive") from last_error


def _verify_head(repo_root: Path, expected_head: str | None) -> str:
    head = _run(["git", "rev-parse", "--verify", "HEAD"], cwd=repo_root, timeout=5).strip()
    if not EXPECTED_HEAD_RE.fullmatch(head):
        raise VerificationError("current HEAD is not a complete commit id")
    if expected_head is not None:
        if not EXPECTED_HEAD_RE.fullmatch(expected_head) or head != expected_head:
            raise VerificationError("current HEAD does not match the expected commit")
    return head


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--java-home", type=Path)
    archive_group = parser.add_mutually_exclusive_group(required=True)
    archive_group.add_argument("--archive", type=Path)
    archive_group.add_argument("--download-archive", action="store_true")
    parser.add_argument("--expected-head")
    args = parser.parse_args(argv)
    try:
        manifest = _read_manifest(args.manifest)
        repo_root = args.repo_root.resolve(strict=True)
        declared_home_value = args.java_home or os.environ.get("JAVA_HOME")
        if not declared_home_value:
            raise VerificationError("JAVA_HOME or --java-home is required")
        java_home = Path(declared_home_value).resolve(strict=True)
        environment_home = os.environ.get("JAVA_HOME")
        if environment_home and Path(environment_home).resolve() != java_home:
            raise VerificationError("JAVA_HOME and --java-home disagree")
        _verify_runtime(java_home, repo_root)
        if args.archive is not None:
            _verify_archive(args.archive.resolve(strict=True))
        else:
            _download_and_verify()
        head = _verify_head(repo_root, args.expected_head)
    except (OSError, VerificationError) as error:
        print(f"toolchain_invalid: {error}", file=sys.stderr)
        return 1

    print(
        "toolchain_valid "
        f"java={manifest['java']['version']} "
        f"vendor={manifest['java']['vendor']} "
        f"archive_sha256={manifest['java']['archive']['sha256']} "
        f"gradle={manifest['gradle']['version']} "
        f"head={head}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
