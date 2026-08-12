#!/usr/bin/env python3
"""Validate the exact reviewed Gradle dependency-verification graph."""

from __future__ import annotations

import argparse
import re
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path


MAX_BYTES = 256 * 1024
SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
NAMESPACE = "{https://schema.gradle.org/dependency-verification}"
XSI_SCHEMA_ATTRIBUTE = "{http://www.w3.org/2001/XMLSchema-instance}schemaLocation"
EXPECTED_SCHEMA_LOCATION = (
    "https://schema.gradle.org/dependency-verification "
    "https://schema.gradle.org/dependency-verification/dependency-verification-1.3.xsd"
)

EXPECTED: dict[tuple[str, str, str], dict[str, str]] = {
    ("org.apiguardian", "apiguardian-api", "1.1.2"): {
        "apiguardian-api-1.1.2.jar": "b509448ac506d607319f182537f0b35d71007582ec741832a1f111e5b5b70b38",
        "apiguardian-api-1.1.2.module": "e08028131375b357d1d28734e9a4fb4216da84b240641cb3ef7e7c7d628223fc",
    },
    ("org.junit", "junit-bom", "5.11.4"): {
        "junit-bom-5.11.4.module": "a9a4f27be94e99b9d570162d246a80f686d277d5d31aeb5481047cf51daf46e4",
        "junit-bom-5.11.4.pom": "19d4b747b204805325b6334553296f986562277a4ac1cb5e593a5e4c4f5e4115",
    },
    ("org.junit.jupiter", "junit-jupiter", "5.11.4"): {
        "junit-jupiter-5.11.4.jar": "aa880e4afba87d447357e4c1fc098c5cb1d200cb9403496c00d3b35a5bd0e8db",
        "junit-jupiter-5.11.4.module": "a3c353ed7516ae1835eab95a087f4f09a5b0cc7d0b8b039fe77a039b8ab52103",
    },
    ("org.junit.jupiter", "junit-jupiter-api", "5.11.4"): {
        "junit-jupiter-api-5.11.4.jar": "ab83ef9e51ac4597d59d26b4b58812129550e2f579a404c8af7d09f5ce5b4293",
        "junit-jupiter-api-5.11.4.module": "a6ea2fefb3aa5868fd7a780ae1da1162e76dda3760b48015c2a419d2372ff3cb",
    },
    ("org.junit.jupiter", "junit-jupiter-engine", "5.11.4"): {
        "junit-jupiter-engine-5.11.4.jar": "cdf8ac59f3fad774ca738ad03890950eeb91833ef0e8908753177edd26f1581c",
        "junit-jupiter-engine-5.11.4.module": "db91163a8af005a32798565dd67537725189590deab6da03b31dbdda45686a18",
    },
    ("org.junit.jupiter", "junit-jupiter-params", "5.11.4"): {
        "junit-jupiter-params-5.11.4.jar": "02a6e015de7ce94ac7f256e7fa05b8091dea861fe79a555a7993313d0f6c7d96",
        "junit-jupiter-params-5.11.4.module": "58865b8b4b998b9ab19c13f8e413b7e1d4819374dd5df69760c4c0b0bc4e9895",
    },
    ("org.junit.platform", "junit-platform-commons", "1.11.4"): {
        "junit-platform-commons-1.11.4.jar": "9edd969b0d0670c54105bc91ae79bd1c6f503e12115faba82073b84c86bbc334",
        "junit-platform-commons-1.11.4.module": "0b9e2625c8f468b3cd4132cc0a805f89fe41f852d1adfff75f3eb1465ca1cb6b",
    },
    ("org.junit.platform", "junit-platform-engine", "1.11.4"): {
        "junit-platform-engine-1.11.4.jar": "b1dd998f64f9acadc15966d9cd3d08074662677b3e390f0a38fcbf0bb4c72330",
        "junit-platform-engine-1.11.4.module": "bf6ce1fb5951dc6c7de36adeef6aeaf78ef82d63831c5ccebce388da9fc5fe25",
    },
    ("org.junit.platform", "junit-platform-launcher", "1.11.4"): {
        "junit-platform-launcher-1.11.4.jar": "d7430bd029e7fcced53ee445e4d2d1a8a1e043ea4c4df43b6335a857f79761ae",
        "junit-platform-launcher-1.11.4.module": "60c4533209ba587b1cda7d72c087f351a3231f9b91c94f3f76394b0e22341cc4",
    },
    ("org.opentest4j", "opentest4j", "1.3.0"): {
        "opentest4j-1.3.0.jar": "48e2df636cab6563ced64dcdff8abb2355627cb236ef0bf37598682ddf742f1b",
        "opentest4j-1.3.0.module": "48bf1d6c8b5dc94f74652bd17900f654deb714350248cf5e8fca27b9090c8e0d",
    },
}


class MetadataError(ValueError):
    pass


def _read(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_BYTES:
        raise MetadataError("verification metadata is missing, symlinked, or oversized")
    data = path.read_bytes()
    if b"\0" in data or not data.endswith(b"\n"):
        raise MetadataError("verification metadata is not bounded UTF-8 text")
    try:
        data.decode("utf-8")
    except UnicodeDecodeError as error:
        raise MetadataError("verification metadata is not UTF-8") from error
    return data


def _verify_tree(root: ET.Element) -> tuple[int, int]:
    if root.tag != NAMESPACE + "verification-metadata" or list(root.attrib) != [XSI_SCHEMA_ATTRIBUTE] or root.attrib != {XSI_SCHEMA_ATTRIBUTE: EXPECTED_SCHEMA_LOCATION}:
        raise MetadataError("verification metadata root is not canonical")
    configuration = list(root)
    if len(configuration) != 2 or configuration[0].tag != NAMESPACE + "configuration" or configuration[1].tag != NAMESPACE + "components":
        raise MetadataError("verification metadata top-level order is not canonical")
    config_children = list(configuration[0])
    if [child.tag for child in config_children] != [NAMESPACE + "verify-metadata", NAMESPACE + "verify-signatures"]:
        raise MetadataError("verification configuration is not canonical")
    if any(child.attrib for child in config_children) or [child.text for child in config_children] != ["true", "false"]:
        raise MetadataError("verification configuration values are not canonical")
    components_element = configuration[1]
    if components_element.attrib:
        raise MetadataError("components element has unexpected attributes")
    components = list(components_element)
    actual: dict[tuple[str, str, str], dict[str, str]] = {}
    previous_key: tuple[str, str, str] | None = None
    for component in components:
        if component.tag != NAMESPACE + "component" or list(component.attrib) != ["group", "name", "version"]:
            raise MetadataError("component coordinates are not canonical")
        key = (component.attrib["group"], component.attrib["name"], component.attrib["version"])
        if previous_key is not None and key <= previous_key:
            raise MetadataError("components are not strictly sorted")
        previous_key = key
        if key in actual:
            raise MetadataError("duplicate dependency component")
        artifacts = list(component)
        values: dict[str, str] = {}
        previous_artifact: str | None = None
        for artifact in artifacts:
            if artifact.tag != NAMESPACE + "artifact" or list(artifact.attrib) != ["name"]:
                raise MetadataError("artifact entry is not canonical")
            name = artifact.attrib["name"]
            if previous_artifact is not None and name <= previous_artifact:
                raise MetadataError("artifacts are not strictly sorted")
            previous_artifact = name
            checksums = list(artifact)
            if len(checksums) != 1 or checksums[0].tag != NAMESPACE + "sha256":
                raise MetadataError("artifact must have exactly one SHA-256")
            checksum = checksums[0]
            if list(checksum.attrib) != ["value", "origin"] or not SHA256_RE.fullmatch(checksum.attrib["value"]):
                raise MetadataError("artifact SHA-256 is malformed")
            if checksum.attrib["origin"] not in {"Generated by Gradle", "Verified from Maven Central download"}:
                raise MetadataError("artifact SHA-256 origin is not reviewed")
            values[name] = checksum.attrib["value"]
        actual[key] = values
    if actual != EXPECTED:
        raise MetadataError("dependency verification graph differs from the reviewed exact graph")
    return len(actual), sum(len(values) for values in actual.values())


def verify_file(path: Path) -> tuple[int, int]:
    try:
        root = ET.fromstring(_read(path))
    except (ET.ParseError, OSError) as error:
        raise MetadataError("verification metadata is not valid XML") from error
    return _verify_tree(root)


def _negative_self_test(path: Path) -> int:
    original = _read(path).decode("utf-8")
    mutations = (
        ("checksum-deletion", original.replace('         </artifact>\n', "", 1)),
        ("checksum-tamper", original.replace("b509448ac506d607319f182537f0b35d71007582ec741832a1f111e5b5b70b38", "0" * 64, 1)),
        ("different-version", original.replace('version="5.11.4"', 'version="5.11.5"', 1)),
        ("unapproved-artifact", original.replace("</components>", '      <component group="example" name="unexpected" version="1.0.0"/>\n   </components>', 1)),
    )
    rejected = 0
    for _name, mutation in mutations:
        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / "verification-metadata.xml"
            candidate.write_text(mutation, encoding="utf-8")
            try:
                verify_file(candidate)
            except MetadataError:
                rejected += 1
            else:
                raise AssertionError(f"dependency metadata mutation was accepted: {_name}")
    return rejected


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("metadata", type=Path)
    args = parser.parse_args(argv)
    try:
        components, artifacts = verify_file(args.metadata)
        negative = _negative_self_test(args.metadata)
    except (OSError, MetadataError, AssertionError) as error:
        print(f"dependency_metadata_invalid: {error}", file=sys.stderr)
        return 1
    print(f"dependency_metadata_valid components={components} artifacts={artifacts} negative_mutations={negative}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
