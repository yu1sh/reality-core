# Changelog

## 0.1.0-SNAPSHOT

- Hardened the public library gate with the exact Eclipse Temurin 17.0.20+8
  toolchain manifest and archive digest, strict structured CI validation,
  bounded source/test/SBOM/publication validators, all-class Java 17 and
  `jdeps` checks, exact Maven staging metadata, and two-pass JAR/SBOM
  reproducibility evidence. The former current-JVM fallback is prohibited;
  the Java API and runtime dependency count remain unchanged.
- Added the pre-public supply-chain gate: immutable GitHub Actions pins,
  fresh-runner online strict followed by offline strict verification, a
  deterministic runtime-only CycloneDX SBOM, public-source safety scanning,
  and CODEOWNERS/issue/PR contribution metadata. The Java API is unchanged;
  JUnit remains test scope and is excluded from the runtime SBOM.
- Hardened the GUI mutation boundary before public release. This is a source
  and API breaking change for the pre-public snapshot: mutation metadata now
  contains only `requestId`, `operationId`, `sessionId`, and `expectedVersion`,
  and `GuiSession.validate` requires the server-authenticated `ActorId`.
  Locale and streamer mode remain server-issued session/snapshot/delta
  presentation state and are no longer accepted in mutation metadata.
- Migration: remove the old locale/streamer arguments from
  `MutationRequestMetadata.of(...)` and call
  `session.validate(metadata, authenticatedActor, now)`. There is no database
  migration. Returning to commit `3eb2e9b6c0583bc3190bb69c29a0e6d503e92a87`
  is a local recovery option only and is prohibited as a formal rollback
  because it restores the unsafe validation boundary.
- Added the initial Minecraft-independent identity, money, revision, result,
  event, authorization, transaction, mutation, and GUI contracts.
- Added deterministic JVM tests and Java 17 release targeting.
- Pinned the Gradle launcher to 9.3.0 with verified distribution checksums.
- Added strict dependency verification metadata and reproducible archive
  settings/checks.
