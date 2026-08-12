#!/usr/bin/env python3
"""Self-tests for public_source_scan.py using runtime-created fixtures."""

from __future__ import annotations

import tempfile
from pathlib import Path

from public_source_scan import ScanError, scan_directory


def _assert_rejected(name: str, content: str | bytes, suffix: str = ".txt") -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / (name + suffix)
        if isinstance(content, bytes):
            path.write_bytes(content)
        else:
            path.write_text(content, encoding="utf-8")
        try:
            findings = scan_directory(Path(directory))
        except ScanError:
            return
        assert findings, (name, findings)


def _assert_rejected_bytes(name: str, content: bytes, suffix: str = ".txt") -> None:
    _assert_rejected(name, content, suffix=suffix)


def main() -> int:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "safe.txt"
        path.write_text("plain source text\n", encoding="utf-8")
        assert scan_directory(Path(directory)) == []

    for key_type in ("RSA", "DSA", "EC", "OPENSSH"):
        _assert_rejected(
            key_type.lower() + "-key",
            "-----BEGIN " + key_type + " " + "PRIVATE KEY-----\n",
        )
    _assert_rejected("pkcs8-key", "-----BEGIN " + "PRIVATE KEY-----\n")
    _assert_rejected("github-token", "gh" + "p_" + "A" * 24)
    _assert_rejected("aws-key", "AK" + "IA" + "A" * 16)
    _assert_rejected("secret", "secret=" + "s" * 24)
    _assert_rejected("posix-path", "/" + "tmp" + "/private-data")
    _assert_rejected(
        "windows-path",
        "C:" + chr(92) + "Users" + chr(92) + "private-data",
    )
    _assert_rejected("unc-path", chr(92) * 2 + "server" + chr(92) + "share")
    _assert_rejected("unlisted-posix-path", "/" + "etc" + "/passwd")
    _assert_rejected("zip-extension", b"source", suffix=".jar")
    _assert_rejected("elf-magic", b"\x7fELF\x02\x01")
    _assert_rejected("rar-magic", b"Rar!\x1a\x07abc")
    _assert_rejected("nul-byte", b"source\0bytes")
    _assert_rejected("control-byte", b"source\x1bbytes")
    _assert_rejected(
        "encrypted-private-key",
        "-----BEGIN " + "ENCRYPTED " + "PRIVATE KEY-----\n",
    )
    _assert_rejected_bytes("utf16", b"\xff\xfeS\x00", suffix=".txt")
    _assert_rejected_bytes("invalid-utf8", b"\xff\xfe\xfd", suffix=".txt")
    _assert_rejected_bytes("oversized", b"x" * (2 * 1024 * 1024 + 1), suffix=".txt")
    _assert_rejected_bytes("long-line", b"x" * (64 * 1024 + 1), suffix=".txt")

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        (root / "A.txt").write_text("source\n", encoding="utf-8")
        (root / "a.txt").write_text("source\n", encoding="utf-8")
        assert scan_directory(root), "case-collision was accepted"

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        target = root / "target.txt"
        target.write_text("source\n", encoding="utf-8")
        link = root / "link.txt"
        try:
            link.symlink_to(target)
        except (OSError, NotImplementedError):
            pass
        else:
            assert scan_directory(root), "symlink was accepted"

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory) / "root"
        root.mkdir()
        (root / "source.txt").write_text("source\n", encoding="utf-8")
        link = Path(directory) / "root-link"
        try:
            link.symlink_to(root, target_is_directory=True)
        except (OSError, NotImplementedError):
            pass
        else:
            try:
                scan_directory(link)
            except ScanError:
                pass
            else:
                raise AssertionError("symlink scan root was accepted")

    _assert_rejected("backslash-path", b"source\n", suffix="sub\\..\\outside.txt")
    print("public_source_scan_self_test=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
