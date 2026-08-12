# reality-core

`reality-core` is the small, Minecraft-independent contract library for the
Reality life simulation platform. It is published as
`io.github.yu1sh.reality:reality-core:0.1.0-SNAPSHOT` and is Java 17 compatible.

## Responsibility

The library owns only contracts that are shared by multiple adapters or
features:

- immutable opaque IDs (`RequestId`, `OperationId`, `CorrelationId`,
  `SessionId`, `ActorId`, `SubjectId`, and `EventId`);
- non-negative `Revision`, event `SchemaVersion`, minor-unit `Money`, and
  `CurrencyCode`;
- structured `Result`/`ErrorInfo` values with stable machine-readable error
  codes and localizable message keys;
- server-side authorization and the minimal `UnitOfWork` transaction port;
- mutation metadata, session validation, and generic GUI snapshot/delta
  contracts; and
- correlation-ready, schema-versioned `DomainEventEnvelope` audit metadata.

The adapters remain responsible for authentication, authorization policy,
idempotency storage, persistence, transport, and localization.

## Explicit non-responsibility

This module does not contain Minecraft, Forge, NeoForge, Bukkit, PostgreSQL,
JSON persistence, GUI screens, screen transitions, or feature services such as
time, life status, economy, jobs, shops, housing, or NPC scheduling. It does
not own database migrations. A Minecraft GameTest is intentionally not part of
this repository: there is no Minecraft integration here, so deterministic JVM
unit/contract tests are the correct verification boundary. Platform adapters
must add their own Forge integration and GameTest coverage.

## GUI mutation boundary

`MutationRequestMetadata` contains exactly the four required mutation fields:
`requestId`, `operationId`, `sessionId`, and `expectedVersion`. It intentionally
does not contain `locale` or `streamerMode`. Those are server-issued
presentation fields carried by `GuiSession`, `GuiSnapshot`, and `GuiDelta`.
Changing presentation state requires a future server-authorized session
reissue or a dedicated query boundary; a mutation packet cannot change it.

`GuiSession.validate` requires the `ActorId` authenticated by the server for
the connection handling the request. The client cannot make a mutation valid by
declaring an actor, locale, or streamer mode in packet metadata.

## Build

Use the reviewed Eclipse Temurin 17.0.20+8 toolchain and the included Gradle
8.8 launcher. The build is intentionally fail-closed when the exact JDK is
not active:

```sh
export JAVA_HOME="$JDK_HOME"
python3 scripts/verify_toolchain.py --manifest toolchain-manifest.json --archive "$JDK_ARCHIVE"
./gradlew --dependency-verification=strict clean check
```

The verifier requires `java`, `javac`, `javadoc`, and `jdeps` to resolve from
the same `JAVA_HOME`, checks vendor `Eclipse Adoptium`, runtime
`17.0.20+8`, the archive SHA-256 in `toolchain-manifest.json`, and the
current Git commit. The compile tasks set `--release 17`. The only dependency
used at runtime is the Java 17 standard library; JUnit Jupiter 5.11.4 and the
JUnit Platform Launcher 1.11.4 are test-only dependencies with fixed
versions. For an offline checkout, retain the verified Gradle ZIP in the
launcher cache before invoking `./gradlew`.

The former current-JVM fallback is prohibited. A maintainer must install or
otherwise provision the exact reviewed JDK and run the verifier before a
build; a different vendor, patch level, runtime, or mixed tool path is a
hard failure.

The launcher accepts only the verified Gradle 8.8 distribution cache. It
rejects `REALITY_GRADLE_HOME`, `GRADLE_HOME`, and PATH executables even when
they report the expected version. Its fallback download requires HTTPS/TLS
and verifies the official Gradle 8.8 binary ZIP against the pinned SHA-256
before extraction; an offline checkout must retain that verified ZIP in the
launcher cache.
The pinned ZIP checksum is
`a4b4158601f8636cdeeab09bd76afb640030bb5b144aafe261a5e8af027dc612`.
The Windows launcher does not auto-download and fails safely when the
verified ZIP is not supplied.

## Dependency verification and reproducibility

`gradle/verification-metadata.xml` is committed and contains SHA-256 checksums
for every resolved Java/JUnit dependency artifact. CI runs strict dependency
verification, so an artifact not present in the reviewed metadata is rejected.

When an intentionally reviewed dependency changes, generate metadata with:

```sh
./gradlew --write-verification-metadata sha256 clean check
git diff -- gradle/verification-metadata.xml
./gradlew --dependency-verification=strict --offline clean check
```

Review that the diff contains only expected coordinates and SHA-256 entries;
do not add `trusted-artifact`, `ignored`, or unsigned exceptions without a
separate security decision. The metadata must remain committed with the
dependency version change.

All Gradle archive tasks disable file timestamps and use reproducible file
ordering. The publication staging POM and module metadata are checked for
exact coordinates, Apache-2.0 licensing, and zero runtime dependencies. To
verify all published artifacts twice locally, use the procedure in
[SUPPLY_CHAIN.md](SUPPLY_CHAIN.md); it checks the main, sources, and Javadoc
JARs, POM, module metadata, and runtime SBOM.

CI performs the same comparison after an online strict clean check and an
offline strict clean check in the same fresh Gradle home.

## Public supply-chain gate

The public workflow is intentionally small and pinned. It runs on a fresh
Ubuntu runner with exact Temurin 17.0.20+8 and Gradle 8.8, verifies the
reviewed JDK archive, performs an online strict dependency-verification
`clean check`, then repeats the same check offline. It also reruns the exact
28 unit/contract tests, Javadoc, all-main-class Java 17 bytecode, `jdeps`,
Maven staging, POM/module validation, source policy, and two-build
reproducibility checks.

`runtimeSbom` writes a canonical CycloneDX 1.5 JSON document at
`build/reports/sbom/reality-core-runtime-sbom.json`. The reviewed runtime
boundary has zero components; JUnit test dependencies cannot enter it. The
CI gate validates duplicate keys, canonical order, version, hashes, paths,
timestamps, and test-scope mutations, then compares its SHA-256 across two
clean builds.

Run the source policy self-tests locally with:

```sh
python3 scripts/public_source_scan.py --repo-root . --tracked-only
python3 scripts/test_public_source_scan.py
python3 scripts/test_runtime_sbom.py
python3 scripts/verify_ci_workflow.py
python3 scripts/verify_dependency_metadata.py gradle/verification-metadata.xml
python3 scripts/verify_toolchain.py --manifest toolchain-manifest.json --archive "$JDK_ARCHIVE"
```

The scanner rejects private-key markers, GitHub/AWS credential patterns,
secret assignments, local absolute paths, binary extensions or magic,
symlinks, case-collisions, UTF-16/invalid UTF-8, and oversized files or
lines. Generated build output is not public source and is excluded from the
tracked source scan.

## Example

An adapter validates all mutation metadata on the server before entering its
transaction boundary, then emits an event with the same correlation chain:

```java
var metadata = MutationRequestMetadata.of(
        RequestId.of("request-42"),
        OperationId.of("purchase-42"), // idempotency key, not the request id
        session.sessionId(),
        session.revision());

ActorId authenticatedActor = connection.authenticatedActor();
Result<Void> validation = session.validate(metadata, authenticatedActor, clock.instant());
if (validation.isFailure()) {
    return validation; // e.g. session_expired or revision_conflict
}

return unitOfWork.execute(() -> {
    // The feature service performs server-side ownership, distance, stock,
    // balance, permission, and cooldown checks here.
    return Result.success();
});
```

For the pre-public `0.1.0-SNAPSHOT` source migration, remove the final
`LocaleTag` and `streamerMode` arguments from
`MutationRequestMetadata.of(...)`, and pass the server-authenticated actor to
`GuiSession.validate(...)`. The old overloads are intentionally removed and
must not be restored because they allow an unauthenticated validation boundary.

`Money` uses minor units and never silently combines currencies:

```java
var price = Money.ofMinorUnits(CurrencyCode.of("CRD"), 125);
var total = price.add(Money.ofMinorUnits(CurrencyCode.of("CRD"), 25));
```

`ErrorInfo.messageKey()` is a localization key, not user-facing Japanese or
English text. `ErrorInfo.toString()` and opaque ID `toString()` methods avoid
putting request/session/actor values or error parameters into logs by default.

## Version policy

These version axes are intentionally independent:

1. The artifact/API release version is the Gradle project version and follows
   SemVer (`0.1.0-SNAPSHOT` here).
2. Event payload compatibility uses `SchemaVersion` inside each event envelope.
3. A network protocol version belongs to the transport/platform adapter; this
   core library does not define a network protocol.
4. A database migration version belongs to the persistence adapter; this core
   library owns no database or migration.

See [COMPATIBILITY.md](COMPATIBILITY.md) for API compatibility and deprecation
rules.

## License

First-party code is Apache-2.0. See [LICENSE](LICENSE), [NOTICE](NOTICE), and
[SECURITY.md](SECURITY.md).
