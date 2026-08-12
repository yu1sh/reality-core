## Change summary

<!-- State the public-readiness or contract problem and the narrow solution. -->

## API signature and invariant evidence

- [ ] `MutationRequestMetadata` remains exactly `requestId`, `operationId`, `sessionId`, `expectedVersion`.
- [ ] `GuiSession.validate(metadata, authenticatedActor, now)` remains the only validation signature.
- [ ] `requestId` and `operationId` semantics are unchanged.
- [ ] Actor/session mismatch, expiry boundary, revision conflict, null handling, and opaque-ID non-leakage remain covered.
- API signature diff/evidence:

## Server authority and presentation state

- Server-authenticated actor source and validation boundary:
- Locale/streamer mode source (`GuiSession`, `GuiSnapshot`, or `GuiDelta`):
- [ ] No client locale/streamer value is accepted as mutation authority.

## Migration and rollback evidence

- Java/API migration:
- Database migration:
- Safe rollback/recovery plan:
- [ ] Rollback does not restore an unauthenticated overload or client-controlled presentation state.

## Supply-chain and public-source evidence

- [ ] Actions use the approved full commit SHAs.
- [ ] Gradle 9.3.0 and Java 17 are unchanged.
- [ ] Fresh-runner online strict verification is followed by offline strict verification.
- [ ] Runtime SBOM is canonical, runtime-only, timestamp/path-free, and has matching two-build SHA-256 values.
- [ ] Public-source scanner and self-tests pass; no secret, binary, or local absolute path was added.
- JAR/SBOM hashes, test count, class major, and `jdeps` result:

## Scope and boundaries

- [ ] No feature service, Minecraft/Forge, database, network codec, or GUI Screen was added.
- [ ] GameTest and real GUI execution are explicitly out of scope where applicable.
- [ ] `git diff --check` and cached diff checks pass.
