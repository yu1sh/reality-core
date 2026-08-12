#!/usr/bin/env python3
"""Validate the exact Maven POM and Gradle module metadata for staging."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any


MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_ARTIFACT_BYTES = 64 * 1024 * 1024
EXPECTED_GROUP = "io.github.yu1sh.reality"
EXPECTED_ARTIFACT = "reality-core"
EXPECTED_VERSION = "0.1.0-SNAPSHOT"
EXPECTED_NAME = "reality-core"
EXPECTED_DESCRIPTION = "Minecraft-independent contracts for the Reality life simulation platform"
EXPECTED_LICENSE_NAME = "Apache License, Version 2.0"
EXPECTED_LICENSE_URL = "https://www.apache.org/licenses/LICENSE-2.0.txt"


class PublicationError(ValueError):
    pass


def _read(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise PublicationError(f"publication file is missing or is a symlink: {path}")
    if path.stat().st_size > MAX_FILE_BYTES:
        raise PublicationError(f"publication file exceeds the bounded limit: {path}")
    data = path.read_bytes()
    if b"\0" in data:
        raise PublicationError(f"publication file contains NUL bytes: {path}")
    return data


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _children(element: ET.Element, name: str) -> list[ET.Element]:
    return [child for child in element if _local(child.tag) == name]


def _one(element: ET.Element, name: str, *, required: bool = True) -> ET.Element | None:
    values = _children(element, name)
    if len(values) > 1 or (required and not values):
        raise PublicationError(f"POM field {name} is missing or duplicated")
    return values[0] if values else None


def _text(element: ET.Element, name: str, *, required: bool = True) -> str | None:
    child = _one(element, name, required=required)
    if child is None:
        return None
    if child.attrib or list(child):
        raise PublicationError(f"POM field {name} is not a scalar")
    value = child.text
    if value is None or value != value.strip():
        raise PublicationError(f"POM field {name} is not canonical text")
    return value


def _verify_pom(path: Path) -> None:
    try:
        root = ET.fromstring(_read(path))
    except (ET.ParseError, OSError) as error:
        raise PublicationError("POM is not valid XML") from error
    if _local(root.tag) != "project" or root.attrib != {
        "{http://www.w3.org/2001/XMLSchema-instance}schemaLocation":
        "http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd"
    }:
        raise PublicationError("POM root is not canonical")
    if [_local(child.tag) for child in root] != [
        "modelVersion",
        "groupId",
        "artifactId",
        "version",
        "name",
        "description",
        "licenses",
    ]:
        raise PublicationError("POM element order or fields are not canonical")
    if _text(root, "modelVersion") != "4.0.0":
        raise PublicationError("POM modelVersion is incorrect")
    if _text(root, "groupId") != EXPECTED_GROUP:
        raise PublicationError("POM groupId is incorrect")
    if _text(root, "artifactId") != EXPECTED_ARTIFACT:
        raise PublicationError("POM artifactId is incorrect")
    if _text(root, "version") != EXPECTED_VERSION:
        raise PublicationError("POM version is incorrect")
    if _text(root, "name") != EXPECTED_NAME:
        raise PublicationError("POM name is incorrect")
    if _text(root, "description") != EXPECTED_DESCRIPTION:
        raise PublicationError("POM description is incorrect")
    licenses = _one(root, "licenses")
    assert licenses is not None
    if licenses.attrib or [_local(child.tag) for child in licenses] != ["license"]:
        raise PublicationError("POM licenses are not canonical")
    license_elements = _children(licenses, "license")
    if len(license_elements) != 1:
        raise PublicationError("POM must contain exactly one license")
    license_element = license_elements[0]
    if [_local(child.tag) for child in license_element] != ["name", "url"]:
        raise PublicationError("POM license fields are not canonical")
    if _text(license_element, "name") != EXPECTED_LICENSE_NAME:
        raise PublicationError("POM license name is incorrect")
    if _text(license_element, "url") != EXPECTED_LICENSE_URL:
        raise PublicationError("POM license URL is incorrect")
    if _children(root, "dependencies"):
        raise PublicationError("runtime POM must not contain dependencies")
    for element in root.iter():
        if element.attrib and element is not root:
            raise PublicationError("POM contains unexpected attributes")


def _json_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise PublicationError("module metadata contains duplicate JSON keys")
        result[key] = value
    return result


def _read_json(path: Path) -> dict[str, Any]:
    data = _read(path)
    try:
        value = json.loads(data.decode("utf-8"), object_pairs_hook=_json_object)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise PublicationError("module metadata is not valid UTF-8 JSON") from error
    if not isinstance(value, dict):
        raise PublicationError("module metadata root must be an object")
    return value


def _artifact_digests(path: Path) -> dict[str, int | str]:
    if path.is_symlink() or not path.is_file():
        raise PublicationError(f"published artifact is missing or is a symlink: {path.name}")
    if path.stat().st_size > MAX_ARTIFACT_BYTES:
        raise PublicationError(f"published artifact exceeds the bounded limit: {path.name}")
    digests = {
        algorithm: hashlib.new(algorithm)
        for algorithm in ("sha512", "sha256", "sha1", "md5")
    }
    size = 0
    try:
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                size += len(chunk)
                if size > MAX_ARTIFACT_BYTES:
                    raise PublicationError(f"published artifact exceeds the bounded limit: {path.name}")
                for digest in digests.values():
                    digest.update(chunk)
    except OSError as error:
        raise PublicationError(f"published artifact could not be read: {path.name}") from error
    if path.stat().st_size != size:
        raise PublicationError(f"published artifact changed while being read: {path.name}")
    return {"size": size, **{algorithm: digest.hexdigest() for algorithm, digest in digests.items()}}


def _verify_module(path: Path, artifact_directory: Path) -> None:
    document = _read_json(path)
    allowed = {"formatVersion", "component", "createdBy", "variants"}
    if set(document) != allowed or list(document) != ["formatVersion", "component", "createdBy", "variants"]:
        raise PublicationError("module metadata top-level shape is not canonical")
    if document["formatVersion"] != "1.1":
        raise PublicationError("module metadata formatVersion is incorrect")
    component = document["component"]
    if not isinstance(component, dict) or list(component) != ["group", "module", "version", "attributes"]:
        raise PublicationError("module component is not canonical")
    if component != {
        "group": EXPECTED_GROUP,
        "module": EXPECTED_ARTIFACT,
        "version": EXPECTED_VERSION,
        "attributes": {"org.gradle.status": "integration"},
    }:
        raise PublicationError("module coordinates are incorrect")
    created_by = document["createdBy"]
    if not isinstance(created_by, dict) or list(created_by) != ["gradle"]:
        raise PublicationError("module creator is not canonical")
    gradle = created_by["gradle"]
    if not isinstance(gradle, dict) or list(gradle) != ["version"] or gradle.get("version") != "8.8":
        raise PublicationError("module was not created by Gradle 8.8")
    variants = document["variants"]
    if not isinstance(variants, list) or not variants:
        raise PublicationError("module variants are missing")
    expected_attributes = [
        {
            "org.gradle.category": "library",
            "org.gradle.dependency.bundling": "external",
            "org.gradle.jvm.version": 17,
            "org.gradle.libraryelements": "jar",
            "org.gradle.usage": "java-api",
        },
        {
            "org.gradle.category": "library",
            "org.gradle.dependency.bundling": "external",
            "org.gradle.jvm.version": 17,
            "org.gradle.libraryelements": "jar",
            "org.gradle.usage": "java-runtime",
        },
        {
            "org.gradle.category": "documentation",
            "org.gradle.dependency.bundling": "external",
            "org.gradle.docstype": "sources",
            "org.gradle.usage": "java-runtime",
        },
        {
            "org.gradle.category": "documentation",
            "org.gradle.dependency.bundling": "external",
            "org.gradle.docstype": "javadoc",
            "org.gradle.usage": "java-runtime",
        },
    ]
    expected_names = ("apiElements", "runtimeElements", "sourcesElements", "javadocElements")
    expected_files = (
        "reality-core-0.1.0-SNAPSHOT.jar",
        "reality-core-0.1.0-SNAPSHOT.jar",
        "reality-core-0.1.0-SNAPSHOT-sources.jar",
        "reality-core-0.1.0-SNAPSHOT-javadoc.jar",
    )
    if len(variants) != len(expected_names):
        raise PublicationError("module variant count is not canonical")
    for index, variant in enumerate(variants):
        if not isinstance(variant, dict):
            raise PublicationError("module variant is not an object")
        if list(variant) != ["name", "attributes", "files"]:
            raise PublicationError("module variant shape is not canonical")
        if variant["name"] != expected_names[index] or variant["attributes"] != expected_attributes[index]:
            raise PublicationError("module variant attributes are not canonical")
        if "dependencies" in variant and variant["dependencies"] != []:
            raise PublicationError("runtime module metadata contains dependencies")
        if "dependencyConstraints" in variant and variant["dependencyConstraints"] != []:
            raise PublicationError("runtime module metadata contains dependency constraints")
        if any("junit" in str(value).lower() for value in variant.values()):
            raise PublicationError("test dependency entered module metadata")
        files = variant["files"]
        if not isinstance(files, list) or len(files) != 1 or not isinstance(files[0], dict):
            raise PublicationError("module variant files are not canonical")
        file = files[0]
        if list(file) != ["name", "url", "size", "sha512", "sha256", "sha1", "md5"]:
            raise PublicationError("module artifact hash shape is not canonical")
        if (
            file["name"] != file["url"]
            or type(file["size"]) is not int
            or file["size"] <= 0
        ):
            raise PublicationError("module artifact file metadata is not canonical")
        if file["name"] != expected_files[index]:
            raise PublicationError("module artifact name is not canonical")
        for algorithm, length in (("sha512", 128), ("sha256", 64), ("sha1", 40), ("md5", 32)):
            if not isinstance(file[algorithm], str) or not re.fullmatch(rf"[0-9a-f]{{{length}}}", file[algorithm]):
                raise PublicationError("module artifact digest is not canonical")
        artifact = artifact_directory / file["name"]
        if artifact.parent != artifact_directory:
            raise PublicationError("module artifact path escapes the build output directory")
        actual = _artifact_digests(artifact)
        expected = {
            "size": file["size"],
            "sha512": file["sha512"],
            "sha256": file["sha256"],
            "sha1": file["sha1"],
            "md5": file["md5"],
        }
        if actual != expected:
            raise PublicationError(f"module hashes do not match {file['name']}")


def verify_publication(staging: Path) -> tuple[Path, Path]:
    directory = staging / EXPECTED_GROUP.replace(".", "/") / EXPECTED_ARTIFACT / EXPECTED_VERSION
    artifact_directory = staging.parent.parent / "libs"
    def one(extension: str) -> Path:
        pattern = re.compile(
            rf"{re.escape(EXPECTED_ARTIFACT)}-0\.1\.0-[0-9]{{8}}\.[0-9]{{6}}-[0-9]+\.{extension}\Z"
        )
        candidates = sorted(path for path in directory.glob(f"*.{extension}") if pattern.fullmatch(path.name))
        if len(candidates) != 1:
            raise PublicationError(f"expected one timestamped staged {extension} file")
        return candidates[0]

    pom = one("pom")
    module = one("module")
    _verify_pom(pom)
    _verify_module(module, artifact_directory)
    return pom, module


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("staging_directory", type=Path)
    args = parser.parse_args(argv)
    try:
        pom, module = verify_publication(args.staging_directory.resolve(strict=True))
    except (OSError, PublicationError) as error:
        print(f"publication_invalid: {error}", file=sys.stderr)
        return 1
    print(f"publication_valid pom={pom.name} module={module.name} runtime_dependencies=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
