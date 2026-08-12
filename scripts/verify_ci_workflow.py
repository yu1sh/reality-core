#!/usr/bin/env python3
"""Parse and fail closed on any change to the public library CI gate."""

from __future__ import annotations

import argparse
import copy
import json
import re
import sys
import tempfile
import unicodedata
from pathlib import Path
from typing import Any


MAX_WORKFLOW_BYTES = 128 * 1024
MAX_WORKFLOW_LINES = 2048
MAX_LINE_BYTES = 16 * 1024
FULL_SHA_RE = re.compile(r"[0-9a-f]{40}\Z")
KEY_RE = re.compile(r"[A-Za-z0-9_.-]+\Z")
CONTROL_BYTE_RE = re.compile(rb"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

EXPECTED_ACTIONS = {
    "actions/checkout": "08eba0b27e820071cde6df949e0beb9ba4906955",
    "actions/setup-java": "c1e323688fd81a25caa38c78aa6df2d33d3e20d9",
    "gradle/actions/setup-gradle": "748248ddd2a24f49513d8f472f81c3a07d4d50e1",
}


class WorkflowError(ValueError):
    pass


def _scalar(value: str) -> Any:
    if value == "":
        return {}
    if value in {"true", "false"}:
        return value == "true"
    if re.fullmatch(r"[0-9]+", value):
        return int(value)
    if value[:1] in {"'", '"'} or value[-1:] in {"'", '"'}:
        raise WorkflowError("quoted YAML scalars are not accepted")
    if value.startswith(("&", "*", "!", "[", "{")) or value in {"null", "~"}:
        raise WorkflowError("unsupported YAML scalar")
    return value


def _split_mapping(line: str) -> tuple[str, str]:
    if ":" not in line:
        raise WorkflowError("mapping line has no colon")
    key, value = line.split(":", 1)
    if not key or key.strip() != key or not KEY_RE.fullmatch(key):
        raise WorkflowError("mapping key is not canonical")
    return key, value[1:] if value.startswith(" ") else value


class _Parser:
    def __init__(self, text: str) -> None:
        if "\r" in text or "\t" in text:
            raise WorkflowError("CR and tab characters are not accepted")
        raw_lines = text.splitlines(keepends=True)
        if len(raw_lines) > MAX_WORKFLOW_LINES:
            raise WorkflowError("workflow line count exceeded the bounded limit")
        self.lines: list[tuple[int, str]] = []
        for number, raw in enumerate(raw_lines, 1):
            if len(raw.encode("utf-8")) > MAX_LINE_BYTES:
                raise WorkflowError(f"workflow line {number} is too long")
            line = raw[:-1] if raw.endswith("\n") else raw
            if line.rstrip() != line:
                raise WorkflowError(f"workflow line {number} has trailing whitespace")
            if not line.strip():
                continue
            indent = len(line) - len(line.lstrip(" "))
            if indent % 2:
                raise WorkflowError(f"workflow line {number} has non-canonical indentation")
            content = line[indent:]
            if content.startswith("#") or " #" in content:
                raise WorkflowError("comments are not accepted in the active workflow")
            if "<<" in content or re.search(r"(^|\s)[&*][A-Za-z0-9_.-]+", content):
                raise WorkflowError("anchors, aliases, and heredocs are not accepted")
            self.lines.append((indent, content))
        if not self.lines:
            raise WorkflowError("workflow is empty")

    def parse(self) -> Any:
        value, index = self._block(0, self.lines[0][0])
        if index != len(self.lines):
            raise WorkflowError("workflow contains an unparsed line")
        return value

    def _block(self, index: int, indent: int) -> tuple[Any, int]:
        if index >= len(self.lines) or self.lines[index][0] != indent:
            raise WorkflowError("unexpected indentation")
        if self.lines[index][1].startswith("- "):
            return self._list(index, indent)
        return self._map(index, indent)

    def _map(self, index: int, indent: int) -> tuple[dict[str, Any], int]:
        result: dict[str, Any] = {}
        while index < len(self.lines) and self.lines[index][0] == indent:
            content = self.lines[index][1]
            if content.startswith("- "):
                break
            key, value = _split_mapping(content)
            if key in result:
                raise WorkflowError(f"duplicate key {key}")
            if value in {"|", "|-", "|+", ">", ">-", ">+"}:
                if value.startswith(">"):
                    raise WorkflowError("folded YAML scalars are not accepted")
                block_lines: list[str] = []
                index += 1
                while index < len(self.lines) and self.lines[index][0] > indent:
                    child_indent, child_content = self.lines[index]
                    if child_indent != indent + 2:
                        raise WorkflowError("block scalar indentation is not canonical")
                    block_lines.append(child_content)
                    index += 1
                result[key] = "\n".join(block_lines) + "\n"
                continue
            if value:
                result[key] = _scalar(value)
                index += 1
                continue
            index += 1
            if index < len(self.lines) and self.lines[index][0] > indent:
                child_indent = self.lines[index][0]
                result[key], index = self._block(index, child_indent)
            else:
                result[key] = {}
        return result, index

    def _list(self, index: int, indent: int) -> tuple[list[Any], int]:
        result: list[Any] = []
        while index < len(self.lines) and self.lines[index][0] == indent:
            content = self.lines[index][1]
            if not content.startswith("- "):
                break
            first = content[2:]
            if not first:
                index += 1
                if index >= len(self.lines) or self.lines[index][0] <= indent:
                    raise WorkflowError("empty list item")
                item, index = self._block(index, self.lines[index][0])
                result.append(item)
                continue
            key, value = _split_mapping(first)
            if key in {"", "-"}:
                raise WorkflowError("invalid list item mapping")
            item: dict[str, Any] = {}
            if value in {"|", "|-", "|+", ">", ">-", ">+"}:
                raise WorkflowError("list item block scalar must be a nested mapping")
            item[key] = _scalar(value) if value else {}
            index += 1
            if not value and index < len(self.lines) and self.lines[index][0] > indent:
                child_indent = self.lines[index][0]
                item[key], index = self._block(index, child_indent)
            if index < len(self.lines) and self.lines[index][0] > indent:
                extra, index = self._map(index, self.lines[index][0])
                for extra_key, extra_value in extra.items():
                    if extra_key in item:
                        raise WorkflowError(f"duplicate list item key {extra_key}")
                    item[extra_key] = extra_value
            result.append(item)
        return result, index


def _parse_workflow(path: Path) -> tuple[Any, str]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_WORKFLOW_BYTES:
        raise WorkflowError("workflow is missing, symlinked, or exceeds the bounded size")
    data = path.read_bytes()
    if CONTROL_BYTE_RE.search(data) or data.startswith(b"\xef\xbb\xbf"):
        raise WorkflowError("workflow must be UTF-8 without BOM or control bytes")
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise WorkflowError("workflow is not UTF-8") from error
    if any(
        unicodedata.category(character) in {"Cc", "Cf"} and character != "\n"
        for character in text
    ):
        raise WorkflowError("workflow contains a control character")
    return _Parser(text).parse(), text


def _expected_workflow() -> dict[str, Any]:
    return {
        "name": "CI",
        "on": {"push": {}, "pull_request": {}},
        "permissions": {"contents": "read"},
        "concurrency": {
            "group": "reality-core-${{ github.workflow }}-${{ github.ref }}",
            "cancel-in-progress": True,
        },
        "jobs": {
            "public-gate": {
                "name": "Public gate",
                "runs-on": "ubuntu-24.04",
                "timeout-minutes": 30,
                "steps": [
                    {
                        "name": "Check out source",
                        "uses": "actions/checkout@08eba0b27e820071cde6df949e0beb9ba4906955",
                    },
                    {
                        "name": "Set up Java 17.0.20+8",
                        "uses": "actions/setup-java@c1e323688fd81a25caa38c78aa6df2d33d3e20d9",
                        "with": {
                            "distribution": "temurin",
                            "java-version": "17.0.20+8",
                            "architecture": "x64",
                            "check-latest": False,
                        },
                    },
                    {
                        "name": "Set up Gradle 9.3.0",
                        "uses": "gradle/actions/setup-gradle@748248ddd2a24f49513d8f472f81c3a07d4d50e1",
                        "with": {"gradle-version": "9.3.0"},
                    },
                    {
                        "name": "Verify exact toolchain and source head",
                        "run": "python3 scripts/verify_toolchain.py --manifest toolchain-manifest.json --download-archive\n",
                    },
                    {
                        "name": "Verify workflow and public source policy",
                        "run": "python3 scripts/verify_ci_workflow.py\n"
                        "python3 scripts/verify_dependency_metadata.py gradle/verification-metadata.xml\n"
                        "python3 scripts/public_source_scan.py --repo-root . --tracked-only\n"
                        "python3 scripts/test_public_source_scan.py\n"
                        "python3 scripts/test_runtime_sbom.py\n",
                    },
                    {
                        "name": "Online strict clean check",
                        "run": "./gradlew --dependency-verification=strict --no-daemon clean check\n",
                    },
                    {
                        "name": "Offline strict clean check",
                        "run": "./gradlew --dependency-verification=strict --offline --no-daemon clean check\n",
                    },
                    {
                        "name": "Re-run the exact unit contract suite",
                        "run": "./gradlew --dependency-verification=strict --offline --no-daemon clean test --rerun-tasks\n",
                    },
                    {
                        "name": "Verify exact unit test report",
                        "run": "python3 scripts/verify_test_report.py build/test-results/test --expected-tests 28\n",
                    },
                    {
                        "name": "Verify Javadoc",
                        "run": "./gradlew --dependency-verification=strict --offline --no-daemon javadoc\n",
                    },
                    {
                        "name": "Verify Java 17 bytecode",
                        "run": "python3 scripts/verify_bytecode.py build/classes/java/main --expected-major 61\n",
                    },
                    {
                        "name": "Verify jdeps",
                        "run": "python3 scripts/verify_jdeps.py build/classes/java/main\n",
                    },
                    {
                        "name": "Stage Maven publication first pass",
                        "run": "./gradlew --dependency-verification=strict --offline --no-daemon clean jar sourcesJar javadocJar publishMavenJavaPublicationToStagingRepository\n"
                        "python3 scripts/verify_publication.py build/staging/repository\n"
                        "python3 scripts/verify_reproducible_outputs.py --write ci-state/artifacts-first.json\n",
                    },
                    {
                        "name": "Stage Maven publication second pass",
                        "run": "./gradlew --dependency-verification=strict --offline --no-daemon clean jar sourcesJar javadocJar publishMavenJavaPublicationToStagingRepository\n"
                        "python3 scripts/verify_publication.py build/staging/repository\n"
                        "python3 scripts/verify_reproducible_outputs.py --compare ci-state/artifacts-first.json\n",
                    },
                    {
                        "name": "Verify runtime SBOM first pass",
                        "run": "./gradlew --dependency-verification=strict --offline --no-daemon clean runtimeSbom\n"
                        "python3 scripts/verify_runtime_sbom.py build/reports/sbom/reality-core-runtime-sbom.json\n"
                        "python3 scripts/verify_reproducible_sbom.py --write ci-state/sbom-first.json\n",
                    },
                    {
                        "name": "Verify runtime SBOM second pass",
                        "run": "./gradlew --dependency-verification=strict --offline --no-daemon clean runtimeSbom\n"
                        "python3 scripts/verify_runtime_sbom.py build/reports/sbom/reality-core-runtime-sbom.json\n"
                        "python3 scripts/verify_reproducible_sbom.py --compare ci-state/sbom-first.json\n",
                    },
                ],
            }
        },
    }


def _assert_exact(expected: Any, actual: Any, path: str = "workflow") -> None:
    if isinstance(expected, dict):
        if not isinstance(actual, dict) or list(actual) != list(expected):
            raise WorkflowError(f"{path} keys/order changed")
        for key in expected:
            _assert_exact(expected[key], actual[key], f"{path}.{key}")
        return
    if isinstance(expected, list):
        if not isinstance(actual, list) or len(actual) != len(expected):
            raise WorkflowError(f"{path} list length changed")
        for index, (expected_item, actual_item) in enumerate(zip(expected, actual)):
            _assert_exact(expected_item, actual_item, f"{path}[{index}]")
        return
    if actual != expected or type(actual) is not type(expected):
        raise WorkflowError(f"{path} value changed")


def _verify_run_lines(workflow: dict[str, Any]) -> None:
    run_values: list[str] = []

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
        elif isinstance(value, str) and value.endswith("\n"):
            run_values.append(value)

    visit(workflow)
    for run in run_values:
        lines = run.splitlines()
        if not lines or any(
            not line
            or line.lstrip().startswith("#")
            or "echo" in line
            or "printf" in line
            or "$(" in line
            or "`" in line
            or "<<" in line
            or ";" in line
            or "&&" in line
            or "||" in line
            or re.search(r"\b(?:env|alias|function|eval|xargs|bash|sh)\b", line)
            for line in lines
        ):
            raise WorkflowError("run contains an unsafe shell wrapper or inactive logical line")
        if any(line.endswith("\\") for line in lines):
            raise WorkflowError("run contains a line continuation")


def _assert_rejected(text: str) -> None:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "ci.yml"
        path.write_text(text, encoding="utf-8")
        try:
            _parse_workflow(path)
        except WorkflowError:
            return
    raise AssertionError("workflow mutation was accepted")


def _negative_self_test(text: str) -> int:
    mutations = [
        ("add-key", text.replace("name: CI\n", "name: CI\nextra: true\n", 1)),
        ("remove-key", text.replace("permissions:\n", "", 1)),
        ("rename-key", text.replace("timeout-minutes:", "timeout:", 1)),
        ("duplicate-key", text.replace("name: CI\n", "name: CI\nname: CI\n", 1)),
        ("unknown-step-key", text.replace("name: Verify jdeps\n", "unknown: true\n        name: Verify jdeps\n", 1)),
        ("action-tag", text.replace("actions/checkout@08eba0b27e820071cde6df949e0beb9ba4906955", "actions/checkout@v4", 1)),
        ("java-version", text.replace("java-version: 17.0.20+8", "java-version: 17", 1)),
        ("vendor", text.replace("distribution: temurin", "distribution: zulu", 1)),
        ("archive-sha", text.replace("--download-archive", "--archive", 1)),
        ("runtime-delete", text.replace("python3 scripts/verify_runtime_sbom.py build/reports/sbom/reality-core-runtime-sbom.json\n", "", 1)),
        ("strict-delete", text.replace("--dependency-verification=strict", "--dependency-verification=off", 1)),
        ("offline-order", text.replace("Stage Maven publication first pass", "Offline strict clean check", 1)),
        ("test-count-delete", text.replace("python3 scripts/verify_test_report.py build/test-results/test --expected-tests 28\n", "", 1)),
        ("jar-command", text.replace(" clean jar sourcesJar", " clean check", 1)),
        ("sbom-command", text.replace("clean runtimeSbom", "clean check", 1)),
        ("staging-command", text.replace("publishMavenJavaPublicationToStagingRepository", "publishToMavenLocal", 1)),
        ("pom-command", text.replace("python3 scripts/verify_publication.py build/staging/repository", "python3 scripts/verify_test_report.py build/test-results/test --expected-tests 28", 1)),
        ("class-command", text.replace("verify_bytecode.py build/classes/java/main --expected-major 61", "verify_bytecode.py build/classes/java/main --expected-major 60", 1)),
        ("jdeps-command", text.replace("verify_jdeps.py build/classes/java/main", "verify_jdeps.py build/classes/java/main --java-home /tmp", 1)),
        ("quoted-placeholder", text.replace("--expected-tests 28", "--expected-tests '28'", 1)),
        ("folded", text.replace("run: |", "run: >", 1)),
        ("comment", text.replace("name: CI\n", "# comment\nname: CI\n", 1)),
        ("wrapper", text.replace("python3 scripts/verify_ci_workflow.py", "bash -c python3 scripts/verify_ci_workflow.py", 1)),
    ]
    for name, mutation in mutations:
        try:
            parsed, _ = _parse_workflow_text(mutation)
            _assert_exact(_expected_workflow(), parsed)
            _verify_run_lines(parsed)
        except WorkflowError:
            continue
        raise AssertionError(f"negative mutation accepted: {name}")
    return len(mutations)


def _negative_manifest_self_test(manifest_path: Path) -> int:
    try:
        document = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise WorkflowError("toolchain manifest cannot be loaded for mutation tests") from error
    mutations = (
        ("temurin-version", ("java", "version"), "17.0.21+9"),
        ("temurin-vendor", ("java", "vendor"), "Other Vendor"),
        ("archive-sha", ("java", "archive", "sha256"), "0" * 64),
        ("archive-url", ("java", "archive", "url"), "https://example.invalid/jdk.tar.gz"),
        ("gradle-version", ("gradle", "version"), "9.2.0"),
    )
    rejected = 0
    for _name, keys, value in mutations:
        mutation = copy.deepcopy(document)
        target: Any = mutation
        for key in keys[:-1]:
            target = target[key]
        target[keys[-1]] = value
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "toolchain-manifest.json"
            path.write_text(json.dumps(mutation), encoding="utf-8")
            try:
                from verify_toolchain import _read_manifest

                _read_manifest(path)
            except (ValueError, OSError):
                rejected += 1
            else:
                raise AssertionError(f"toolchain mutation accepted: {_name}")
    return rejected


def _parse_workflow_text(text: str) -> tuple[Any, str]:
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "ci.yml"
        path.write_text(text, encoding="utf-8")
        return _parse_workflow(path)


def verify_workflow(path: Path) -> int:
    actual, text = _parse_workflow(path)
    _assert_exact(_expected_workflow(), actual)
    _verify_run_lines(actual)
    count = _negative_self_test(text)
    manifest_path = path.resolve().parents[2] / "toolchain-manifest.json"
    if manifest_path.is_file():
        count += _negative_manifest_self_test(manifest_path)
    return count


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workflow", type=Path)
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    path = args.workflow or root / ".github" / "workflows" / "ci.yml"
    try:
        negative_count = verify_workflow(path)
    except (OSError, WorkflowError, AssertionError) as error:
        print(f"ci_workflow_invalid: {error}", file=sys.stderr)
        return 1
    print(f"ci_workflow_policy=ok action_count=3 negative_mutations={negative_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
