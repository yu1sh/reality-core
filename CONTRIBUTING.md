# Contributing

Keep this module Minecraft- and database-independent. New public contracts
must have a clear shared ownership case across multiple adapters or features;
feature-owned services belong elsewhere.

Before submitting a change:

```sh
python3 scripts/verify_toolchain.py --manifest toolchain-manifest.json --archive "$JDK_ARCHIVE"
./gradlew --dependency-verification=strict clean check
./gradlew --dependency-verification=strict --offline --no-daemon clean test --rerun-tasks
python3 scripts/verify_test_report.py build/test-results/test --expected-tests 28
python3 scripts/verify_dependency_metadata.py gradle/verification-metadata.xml
./gradlew --dependency-verification=strict --offline --no-daemon javadoc
python3 scripts/verify_bytecode.py build/classes/java/main --expected-major 61
python3 scripts/verify_jdeps.py build/classes/java/main
./gradlew --dependency-verification=strict --offline --no-daemon clean jar sourcesJar javadocJar publishMavenJavaPublicationToStagingRepository
python3 scripts/verify_publication.py build/staging/repository
python3 scripts/verify_reproducible_outputs.py --write ci-state/artifacts-first.json
python3 scripts/public_source_scan.py --repo-root . --tracked-only
python3 scripts/test_public_source_scan.py
python3 scripts/test_runtime_sbom.py
python3 scripts/verify_ci_workflow.py
git diff --check
```

Use deterministic clocks and inputs in tests. Do not put localized display
sentences, secrets, coordinates, or third-party binaries in the core module.
Update `COMPATIBILITY.md` and `CHANGELOG.md` for public API or invariant
changes.

Dependency changes must regenerate and review the committed
`gradle/verification-metadata.xml`:

```sh
./gradlew --write-verification-metadata sha256 clean check
git diff -- gradle/verification-metadata.xml
./gradlew --dependency-verification=strict --offline clean check
```

Only expected dependency coordinates and SHA-256 values may be added. Do not
use trusted or ignored artifact exceptions as a shortcut. Before submitting a
build-system change, run the two-build JAR hash comparison documented in the
README and confirm both hashes match. Run `runtimeSbom` twice from clean
builds and confirm its hashes match as well. The public CI gate must retain its
online strict then offline strict order, minimal read-only permissions,
timeout, and cancel-in-progress concurrency policy.

The public API contract is frozen for this hardening line. Do not change the
four-field `MutationRequestMetadata` factory or the
`GuiSession.validate(metadata, authenticatedActor, now)` signature. Locale and
streamer mode belong to server-issued session/snapshot/delta presentation
state, not mutation metadata. Any future API change needs the migration and
rollback evidence required by `COMPATIBILITY.md`.

The former current-JVM fallback is prohibited. Use the exact JDK verifier and
the rollback procedure in [SUPPLY_CHAIN.md](SUPPLY_CHAIN.md); do not commit
Gradle, JDK, generated, or third-party binary files.
