#!/usr/bin/env python3
"""Verify the exact JUnit test count and a zero-failure test report."""

from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


MAX_REPORT_FILES = 128
MAX_REPORT_BYTES = 8 * 1024 * 1024
MAX_REPORT_DEPTH = 16


class ReportError(ValueError):
    pass


def _depth(element: ET.Element, current: int = 0) -> int:
    if current > MAX_REPORT_DEPTH:
        raise ReportError("JUnit XML nesting is too deep")
    return max((_depth(child, current + 1) for child in element), default=current)


def _integer(element: ET.Element, name: str) -> int:
    value = element.attrib.get(name)
    if value is None or not value.isdecimal():
        raise ReportError(f"JUnit suite has no non-negative integer {name}")
    return int(value)


def verify_report(directory: Path, expected_tests: int) -> tuple[int, int, int, int, int]:
    if expected_tests <= 0:
        raise ReportError("expected test count must be positive")
    if not directory.is_dir() or directory.is_symlink():
        raise ReportError("JUnit report directory is missing or is a symlink")
    files = sorted(directory.glob("*.xml"))
    if not files or len(files) > MAX_REPORT_FILES:
        raise ReportError("JUnit report file count is outside the bounded range")

    suites = tests = failures = errors = skipped = 0
    for path in files:
        if path.is_symlink() or not path.is_file():
            raise ReportError("JUnit report contains a symlink or non-file")
        if path.stat().st_size > MAX_REPORT_BYTES:
            raise ReportError("JUnit report is larger than the bounded limit")
        try:
            root = ET.parse(path).getroot()
        except (ET.ParseError, OSError) as error:
            raise ReportError(f"invalid JUnit XML: {path.name}") from error
        _depth(root)
        suite_elements = [root] if root.tag == "testsuite" else list(root) if root.tag == "testsuites" else []
        if not suite_elements or any(suite.tag != "testsuite" for suite in suite_elements):
            raise ReportError("JUnit XML has an unsupported root structure")
        for suite in suite_elements:
            declared_tests = _integer(suite, "tests")
            declared_failures = _integer(suite, "failures")
            declared_errors = _integer(suite, "errors")
            declared_skipped = _integer(suite, "skipped")
            cases = [child for child in suite if child.tag == "testcase"]
            if declared_tests != len(cases):
                raise ReportError(f"JUnit suite test declaration disagrees with testcases: {path.name}")
            actual_failures = sum(1 for case in cases if any(child.tag == "failure" for child in case))
            actual_errors = sum(1 for case in cases if any(child.tag == "error" for child in case))
            actual_skipped = sum(1 for case in cases if any(child.tag == "skipped" for child in case))
            if (declared_failures, declared_errors, declared_skipped) != (
                actual_failures,
                actual_errors,
                actual_skipped,
            ):
                raise ReportError(f"JUnit suite result declaration disagrees with testcases: {path.name}")
            suites += 1
            tests += declared_tests
            failures += declared_failures
            errors += declared_errors
            skipped += declared_skipped

    if tests != expected_tests or failures != 0 or errors != 0 or skipped != 0:
        raise ReportError(
            f"expected {expected_tests} passing tests, got tests={tests} "
            f"failures={failures} errors={errors} skipped={skipped}"
        )
    return suites, tests, failures, errors, skipped


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report_directory", type=Path)
    parser.add_argument("--expected-tests", type=int, required=True)
    args = parser.parse_args(argv)
    try:
        suites, tests, failures, errors, skipped = verify_report(
            args.report_directory, args.expected_tests
        )
    except (OSError, ReportError) as error:
        print(f"test_report_invalid: {error}", file=sys.stderr)
        return 1
    print(
        f"test_report_valid suites={suites} tests={tests} "
        f"failures={failures} errors={errors} skipped={skipped}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
