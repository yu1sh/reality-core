# Public supply-chain gate

This library gate is intentionally fail-closed. It covers the Java toolchain,
Gradle dependency inputs, source files, tests, publication metadata, bytecode,
module dependencies, and reproducible outputs. It does not change the
Minecraft-independent Java API.

## Reviewed inputs

The exact inputs are recorded in [toolchain-manifest.json](toolchain-manifest.json):

- Eclipse Temurin 17.0.20+8, vendor `Eclipse Adoptium`, Java release 17,
  class-file major 61;
- Linux x64 archive SHA-256
  `be7668bc030d578b83d6d5ef9221d6d6729bbbca8cf94a7d52e16ac68b5a5a35`;
- Gradle 9.3.0 and its verified launcher distribution; and
- JUnit Jupiter 5.11.4 and JUnit Platform Launcher 1.11.4 at test scope only.

The former current-JVM escape hatch is forbidden. The exact JDK must be
installed or provisioned before Gradle is run; the build never silently
substitutes the host JVM. `verify_toolchain.py` checks all four executable
paths (`java`, `javac`, `javadoc`, and `jdeps`) against one canonical
`JAVA_HOME`, exact vendor/version properties, the archive digest, and a
complete current Git HEAD.

## Dependency verification

`gradle/verification-metadata.xml` contains SHA-256 entries only for the
reviewed JUnit graph and its metadata. Strict mode is required for every
Gradle gate. The intended evidence sequence is:

1. online `clean check` with strict verification in a fresh empty Gradle home;
2. offline strict `clean check` in that same home;
3. offline strict test rerun with `--rerun-tasks` and XML verification of
   exactly 28 tests with zero failures, errors, or skips; and
4. offline strict Javadoc and publication staging.

No broad trust pattern, PGP trust-all rule, ignored artifact, or unreviewed
version is permitted. A dependency change must regenerate the metadata and
must be reviewed as a coordinate-and-digest-only diff.
`verify_dependency_metadata.py` also checks the exact 10-component,
20-artifact graph and runs checksum deletion, tamper, version, and unapproved
artifact mutation tests.

## Artifact evidence

The staging gate validates the main, sources, and Javadoc JARs plus the POM
and Gradle module metadata. It rejects unsafe ZIP names, duplicate or
unsorted entries, non-fixed entry timestamps, local paths, build timestamps,
private-key markers, and content changes. The POM must have the exact
coordinates, name, description, Apache-2.0 URL, and no runtime dependency.
The module metadata must be created by Gradle 9.3.0 and contain no runtime or
test dependency.

The runtime SBOM is canonical CycloneDX 1.5 JSON. It contains the root
`reality-core` component and zero runtime components. Its validator rejects
duplicate JSON keys, extra/missing/reordered keys, version/hash mutations,
timestamps, serial numbers, local paths, and JUnit content. The first and
second clean publication/SBOM builds are SHA-256 compared.

## Source and CI policy

The workflow parser accepts only the reviewed YAML subset and exact job/step
shape. It rejects aliases, anchors, folded scalars, comments, shell wrappers,
command substitutions, mutable action references, unknown keys, duplicate or
renamed steps, and moved or weakened commands. Its mutation self-test covers
workflow structure, action pins, toolchain values, strict/offline ordering,
test-count verification, bytecode, `jdeps`, staging, POM, and SBOM commands.

The tracked-source scanner is bounded by file count, directory depth, path
length, file size, and line length. It rejects symlinks, case-collisions,
NUL/UTF-16/invalid UTF-8, binary/archive content, credentials, private keys,
local absolute paths, and oversized inputs.

## Rollback and scope

There is no database, world, network, or artifact migration. Rollback is the
revert of this single hardening commit. GUI, Forge, GameTest, dedicated-server,
real-client, PostgreSQL, and screenshot evidence are not applicable to this
Minecraft-independent library; platform adapters own those tests.
