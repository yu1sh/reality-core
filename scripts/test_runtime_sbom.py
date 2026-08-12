#!/usr/bin/env python3
"""Self-tests for the runtime SBOM validator."""

from __future__ import annotations

import copy
import tempfile
from pathlib import Path

from verify_runtime_sbom import ValidationError, validate_document, validate_file


SAFE_DOCUMENT = {
    "bomFormat": "CycloneDX",
    "specVersion": "1.5",
    "version": 1,
    "metadata": {
        "component": {
            "type": "library",
            "group": "io.github.yu1sh.reality",
            "name": "reality-core",
            "version": "0.1.0-SNAPSHOT",
            "bom-ref": "pkg:maven/io.github.yu1sh.reality/reality-core@0.1.0-SNAPSHOT",
            "purl": "pkg:maven/io.github.yu1sh.reality/reality-core@0.1.0-SNAPSHOT",
        }
    },
    "components": [],
    "dependencies": [
        {
            "ref": "pkg:maven/io.github.yu1sh.reality/reality-core@0.1.0-SNAPSHOT",
            "dependsOn": [],
        }
    ],
}


def _assert_invalid(document: dict) -> None:
    try:
        validate_document(document)
    except ValidationError:
        return
    raise AssertionError("invalid SBOM was accepted")


def main() -> int:
    validate_document(copy.deepcopy(SAFE_DOCUMENT))

    extra_key_document = copy.deepcopy(SAFE_DOCUMENT)
    extra_key_document["extra"] = True
    _assert_invalid(extra_key_document)

    missing_key_document = copy.deepcopy(SAFE_DOCUMENT)
    del missing_key_document["dependencies"]
    _assert_invalid(missing_key_document)

    reordered_document = {
        "dependencies": SAFE_DOCUMENT["dependencies"],
        "bomFormat": SAFE_DOCUMENT["bomFormat"],
        "specVersion": SAFE_DOCUMENT["specVersion"],
        "version": SAFE_DOCUMENT["version"],
        "metadata": SAFE_DOCUMENT["metadata"],
        "components": SAFE_DOCUMENT["components"],
    }
    _assert_invalid(reordered_document)

    version_document = copy.deepcopy(SAFE_DOCUMENT)
    version_document["version"] = 2
    _assert_invalid(version_document)

    junit_document = copy.deepcopy(SAFE_DOCUMENT)
    junit_document["components"] = [
        {
            "scope": "required",
            "bom-ref": "pkg:maven/org.junit/junit-bom@5.11.4",
            "purl": "pkg:maven/org.junit/junit-bom@5.11.4",
            "group": "org.junit",
            "name": "junit-bom",
            "version": "5.11.4",
        }
    ]
    junit_document["dependencies"][0]["dependsOn"] = [
        "pkg:maven/org.junit/junit-bom@5.11.4"
    ]
    _assert_invalid(junit_document)

    timestamp_document = copy.deepcopy(SAFE_DOCUMENT)
    timestamp_document["metadata"]["timestamp"] = "2026-01-01T00:00:00Z"
    _assert_invalid(timestamp_document)

    path_document = copy.deepcopy(SAFE_DOCUMENT)
    absolute_path = "/" + "tmp" + "/local"
    path_document["metadata"]["component"]["bom-ref"] = absolute_path
    path_document["metadata"]["component"]["purl"] = absolute_path
    path_document["dependencies"][0]["ref"] = absolute_path
    _assert_invalid(path_document)

    relationship_document = copy.deepcopy(SAFE_DOCUMENT)
    relationship_document["dependencies"][0]["dependsOn"] = ["unexpected"]
    _assert_invalid(relationship_document)

    hash_document = copy.deepcopy(SAFE_DOCUMENT)
    hash_document["components"] = [
        {
            "type": "library",
            "group": "example",
            "name": "dependency",
            "version": "1.0.0",
            "scope": "required",
            "bom-ref": "pkg:maven/example/dependency@1.0.0",
            "purl": "pkg:maven/example/dependency@1.0.0",
            "hashes": [{"alg": "SHA-256", "content": "0" * 64}],
        }
    ]
    hash_document["dependencies"][0]["dependsOn"] = [
        "pkg:maven/example/dependency@1.0.0"
    ]
    _assert_invalid(hash_document)

    with tempfile.TemporaryDirectory() as directory:
        duplicate = Path(directory) / "duplicate.json"
        duplicate.write_text(
            '{"bomFormat":"CycloneDX","bomFormat":"CycloneDX",'
            '"specVersion":"1.5","version":1,"metadata":{},'
            '"components":[],"dependencies":[]}',
            encoding="utf-8",
        )
        try:
            validate_file(duplicate)
        except ValidationError:
            pass
        else:
            raise AssertionError("duplicate JSON key was accepted")

    print("runtime_sbom_self_test=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
