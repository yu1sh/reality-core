#!/usr/bin/env python3
"""Reject secrets, local paths, symlinks, binary content, and unsafe inputs."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import unicodedata
from pathlib import Path
from typing import Iterable


MAX_FILES = 4096
MAX_DIRECTORIES = 4096
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_GIT_OUTPUT_BYTES = 4 * 1024 * 1024
MAX_PATH_BYTES = 1024
MAX_PATH_DEPTH = 32
MAX_LINE_BYTES = 64 * 1024
MAX_SUBPROCESS_OUTPUT_BYTES = 128 * 1024

BINARY_EXTENSIONS = frozenset(
    {
        ".7z",
        ".bin",
        ".bz2",
        ".class",
        ".dll",
        ".dylib",
        ".exe",
        ".gif",
        ".gz",
        ".ico",
        ".jar",
        ".jpeg",
        ".jpg",
        ".keystore",
        ".mp3",
        ".mp4",
        ".otf",
        ".p12",
        ".pdf",
        ".png",
        ".so",
        ".tar",
        ".tgz",
        ".ttf",
        ".woff",
        ".woff2",
        ".xz",
        ".zip",
    }
)

BINARY_MAGICS = (
    (b"\x7fELF", "ELF binary"),
    (b"MZ", "PE/DOS binary"),
    (b"PK\x03\x04", "ZIP container"),
    (b"Rar!\x1a\x07", "RAR container"),
    (b"7z\xbc\xaf\x27\x1c", "7-Zip container"),
    (b"\x1f\x8b", "gzip stream"),
    (b"BZh", "bzip2 stream"),
    (b"\xfd7zXZ\x00", "XZ stream"),
    (b"%PDF-", "PDF document"),
    (b"\x89PNG\r\n\x1a\n", "PNG image"),
    (b"\xff\xd8\xff", "JPEG image"),
    (b"GIF8", "GIF image"),
    (b"\xca\xfe\xba\xbe", "Java class file"),
    (b"\xcf\xfa\xed\xfe", "Mach-O binary"),
    (b"\xfe\xed\xfa\xcf", "Mach-O binary"),
)

PRIVATE_KEY_RE = re.compile(r"-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY-----")

GITHUB_TOKEN_PREFIXES = tuple(
    "gh" + suffix for suffix in ("p_", "o_", "u_", "s_", "r_")
) + ("github" + "_pat_",)
GITHUB_TOKEN_RE = re.compile(
    r"\b(?:"
    + "|".join(re.escape(prefix) for prefix in GITHUB_TOKEN_PREFIXES)
    + r")[A-Za-z0-9_]{20,}\b"
)

AWS_ACCESS_KEY_PREFIXES = ("AK" + "IA", "AS" + "IA")
AWS_ACCESS_KEY_RE = re.compile(
    r"\b(?:" + "|".join(AWS_ACCESS_KEY_PREFIXES) + r")[0-9A-Z]{16}\b"
)
AWS_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(?:aws[_-]?(?:access[_-]?key[_-]?id|secret[_-]?access[_-]?key))\b"
    r"\s*[:=]\s*['\"]?[A-Za-z0-9/+=]{16,}"
)
SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(?:password|passwd|secret|token|api[_-]?key)\b"
    r"\s*[:=]\s*['\"]?[^\s'\"`]{8,}"
)

POSIX_ROOT_NAMES = (
    "bin",
    "boot",
    "data",
    "etc",
    "home",
    "lib",
    "lib32",
    "lib64",
    "media",
    "mnt",
    "opt",
    "proc",
    "project",
    "projects",
    "repo",
    "repos",
    "root",
    "run",
    "sbin",
    "src",
    "srv",
    "sys",
    "tmp",
    "usr",
    "var",
    "work",
    "workspace",
    "workspaces",
    "Users",
)
POSIX_ABSOLUTE_RE = re.compile(
    r"(?<![A-Za-z0-9_])/(?:" + "|".join(POSIX_ROOT_NAMES) + r")(?:/|$)"
)
POSIX_MULTI_SEGMENT_RE = re.compile(
    r"(?<![A-Za-z0-9_/:.<])/(?!/)"
    r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*"
)
WINDOWS_ABSOLUTE_RE = re.compile(r"(?<![A-Za-z0-9_])[A-Za-z]:[\\/]")
UNC_ABSOLUTE_RE = re.compile(
    r"(?<![A-Za-z0-9_])"
    + chr(92) * 4
    + r"[A-Za-z0-9_.-]+["
    + chr(92) * 2
    + r"/]"
)
UTF16_BOMS = (b"\xff\xfe", b"\xfe\xff", b"\xff\xfe\x00\x00", b"\x00\x00\xfe\xff")
CONTROL_BYTE_RE = re.compile(rb"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
EXCLUDED_DIRECTORIES = frozenset({".git", ".gradle", "build", "ci-state", "__pycache__"})


class ScanError(ValueError):
    pass


def _finding(relative_path: str, reason: str) -> str:
    return relative_path + ": " + reason


def _has_unsafe_controls(value: str) -> bool:
    return any(
        unicodedata.category(character) in {"Cc", "Cf"}
        and character not in "\t\n\r"
        for character in value
    )


def _check_path(relative_path: str) -> None:
    try:
        encoded_length = len(relative_path.encode("utf-8", errors="strict"))
    except UnicodeEncodeError as error:
        raise ScanError("path is not valid UTF-8") from error
    parts = Path(relative_path).parts
    if encoded_length > MAX_PATH_BYTES:
        raise ScanError(f"path exceeds the {MAX_PATH_BYTES}-byte limit")
    if len(parts) > MAX_PATH_DEPTH:
        raise ScanError(f"path exceeds the {MAX_PATH_DEPTH}-component depth limit")
    if (
        not relative_path
        or relative_path.startswith(("/", "\\"))
        or "\0" in relative_path
        or "\\" in relative_path
        or ":" in relative_path
        or _has_unsafe_controls(relative_path)
    ):
        raise ScanError("path is absolute or contains an unsafe separator or control")
    if any(part in {"", ".", ".."} for part in parts):
        raise ScanError("path contains an unsafe component")


def _run_git(command: list[str], cwd: Path) -> bytes:
    try:
        process = subprocess.Popen(
            command,
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        assert process.stdout is not None
        output = process.stdout.read(MAX_GIT_OUTPUT_BYTES + 1)
        if len(output) > MAX_GIT_OUTPUT_BYTES:
            process.kill()
            process.wait(timeout=5)
            raise ScanError("git tracked path output exceeded the bounded limit")
        stderr = process.stderr.read(MAX_SUBPROCESS_OUTPUT_BYTES + 1) if process.stderr else b""
        return_code = process.wait(timeout=5)
    except (OSError, subprocess.SubprocessError) as error:
        raise ScanError("git path enumeration failed") from error
    if len(stderr) > MAX_SUBPROCESS_OUTPUT_BYTES or return_code != 0:
        raise ScanError("git path enumeration failed")
    return output


def _tracked_relative_paths(root: Path) -> list[str]:
    root = root.resolve(strict=True)
    top_output = _run_git(["git", "rev-parse", "--show-toplevel"], root)
    try:
        repository_root = Path(top_output.decode("utf-8").strip()).resolve(strict=True)
    except UnicodeDecodeError as error:
        raise ScanError("git repository root was not UTF-8") from error
    try:
        prefix = root.relative_to(repository_root).as_posix()
    except ValueError as error:
        raise ScanError("scan root is outside the git worktree") from error
    command = ["git", "ls-files", "-z"]
    if prefix:
        command += ["--", prefix]
    else:
        command += ["--", "."]
    output = _run_git(command, repository_root)
    paths: list[str] = []
    for raw_path in output.split(b"\0"):
        if not raw_path:
            continue
        try:
            repository_path = raw_path.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ScanError("git tracked path is not UTF-8") from error
        relative = repository_path[len(prefix) + 1 :] if prefix else repository_path
        if prefix and (not repository_path.startswith(prefix + "/") or not relative):
            raise ScanError("git returned a path outside the scan root")
        _check_path(relative)
        paths.append(relative)
    if not paths or len(paths) > MAX_FILES:
        raise ScanError("tracked file count is outside the bounded range")
    return sorted(paths)


def _tracked_paths(root: Path) -> Iterable[Path]:
    for relative in _tracked_relative_paths(root):
        yield root / relative


def _source_paths(root: Path, tracked_only: bool) -> Iterable[Path]:
    root = root.resolve(strict=True)
    if tracked_only:
        yield from _tracked_paths(root)
        return

    paths: list[Path] = []
    directories = 0
    stack: list[tuple[Path, int]] = [(root, 0)]
    while stack:
        directory, depth = stack.pop()
        directories += 1
        if directories > MAX_DIRECTORIES:
            raise ScanError("directory count exceeded the bounded limit")
        try:
            entries = sorted(os.scandir(directory), key=lambda item: item.name)
        except OSError as error:
            raise ScanError(f"cannot enumerate {directory}") from error
        if len(entries) > MAX_FILES:
            raise ScanError("directory entry count exceeded the bounded limit")
        for entry in entries:
            relative = Path(entry.path).relative_to(root).as_posix()
            _check_path(relative)
            if entry.is_symlink():
                paths.append(Path(entry.path))
                continue
            if entry.is_dir(follow_symlinks=False):
                if entry.name not in EXCLUDED_DIRECTORIES:
                    if depth + 1 > MAX_PATH_DEPTH:
                        raise ScanError("directory depth exceeded the bounded limit")
                    stack.append((Path(entry.path), depth + 1))
            elif entry.is_file(follow_symlinks=False):
                paths.append(Path(entry.path))
    if len(paths) > MAX_FILES:
        raise ScanError("file count exceeded the bounded limit")
    yield from sorted(paths, key=lambda path: path.relative_to(root).as_posix())


def _scan_file(path: Path, relative_path: str) -> list[str]:
    findings: list[str] = []
    try:
        if path.is_symlink():
            return [_finding(relative_path, "symlink is not public source")]
        if not path.is_file():
            return [_finding(relative_path, "tracked path is not a regular file")]
        size = path.stat().st_size
        if size > MAX_FILE_BYTES:
            return [_finding(relative_path, "file exceeds the bounded size limit")]
        data = path.read_bytes()
    except OSError as error:
        return [_finding(relative_path, f"file could not be read: {error.__class__.__name__}")]
    if path.suffix.lower() in BINARY_EXTENSIONS:
        findings.append(_finding(relative_path, "binary extension is not public source"))
    for magic, description in BINARY_MAGICS:
        if data.startswith(magic):
            findings.append(_finding(relative_path, description + " detected"))
    if CONTROL_BYTE_RE.search(data):
        findings.append(_finding(relative_path, "control byte is not public source"))
    if data.startswith(UTF16_BOMS):
        findings.append(_finding(relative_path, "UTF-16/32 encoding is not public source"))
    if data.startswith(b"\xef\xbb\xbf"):
        findings.append(_finding(relative_path, "UTF-8 BOM is not public source"))
    if any(len(line) > MAX_LINE_BYTES for line in data.split(b"\n")):
        findings.append(_finding(relative_path, "line exceeds the bounded length limit"))

    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        findings.append(_finding(relative_path, "file is not UTF-8 text"))
        return findings
    if _has_unsafe_controls(text):
        findings.append(_finding(relative_path, "control character is not public source"))

    checks = (
        (PRIVATE_KEY_RE, "private-key marker"),
        (GITHUB_TOKEN_RE, "GitHub token pattern"),
        (AWS_ACCESS_KEY_RE, "AWS access-key pattern"),
        (AWS_ASSIGNMENT_RE, "AWS credential assignment"),
        (SECRET_ASSIGNMENT_RE, "secret assignment"),
        (POSIX_ABSOLUTE_RE, "POSIX local absolute path"),
        (POSIX_MULTI_SEGMENT_RE, "POSIX local absolute path"),
        (WINDOWS_ABSOLUTE_RE, "Windows local absolute path"),
        (UNC_ABSOLUTE_RE, "UNC local absolute path"),
    )
    for pattern, reason in checks:
        match = pattern.search(text)
        first_line_end = text.find("\n") if "\n" in text else len(text)
        is_shebang_path = (
            pattern in {POSIX_ABSOLUTE_RE, POSIX_MULTI_SEGMENT_RE}
            and text.startswith("#!")
            and match is not None
            and match.start() < first_line_end
        )
        if match and not is_shebang_path and match.group(0) != "/dev/null":
            findings.append(_finding(relative_path, reason))
    return findings


def scan_directory(root: Path, tracked_only: bool = False) -> list[str]:
    if root.is_symlink():
        raise ScanError("scan root must not be a symlink")
    root = root.resolve(strict=True)
    if not root.is_dir():
        raise ScanError("scan root must be a directory")
    findings: list[str] = []
    seen_casefolded: dict[str, str] = {}
    paths = list(_source_paths(root, tracked_only))
    if len(paths) > MAX_FILES:
        raise ScanError("file count exceeded the bounded limit")
    for path in paths:
        relative_path = path.relative_to(root).as_posix()
        normalized = unicodedata.normalize("NFC", relative_path).casefold()
        previous = seen_casefolded.get(normalized)
        if previous is not None and previous != relative_path:
            findings.append(_finding(relative_path, f"case-collision with {previous}"))
        else:
            seen_casefolded[normalized] = relative_path
        findings.extend(_scan_file(path, relative_path))
    return findings


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--tracked-only", action="store_true")
    args = parser.parse_args(argv)
    try:
        findings = scan_directory(args.repo_root, tracked_only=args.tracked_only)
    except (OSError, ScanError) as error:
        print(f"public_source_scan_invalid: {error}", file=sys.stderr)
        return 1
    if findings:
        for finding in findings:
            print(finding, file=sys.stderr)
        return 1
    print("public_source_scan=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
