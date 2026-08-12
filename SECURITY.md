# Security policy

Do not report vulnerabilities in request metadata, identifiers, or deployment
configuration in a public issue. Send a private report to the repository
maintainer with reproduction steps, affected version, and impact.

The core library deliberately treats all client metadata as untrusted input.
Adapters must authenticate the actor, re-check permissions and resource
ownership on the server, enforce idempotency for `OperationId`, and persist
auditable event envelopes atomically with their mutation.

## Public-source and build integrity

The repository's public-source scanner rejects private-key markers, GitHub and
AWS credential patterns, secret assignments, local absolute paths, and binary
content. It runs against Git-tracked source files in CI and has runtime-created
self-test fixtures; no test secret or binary is committed.

The CI workflow pins every action to a reviewed full commit SHA, fixes
Eclipse Temurin 17.0.20+8 and Gradle 8.8, verifies the JDK archive digest,
and runs strict dependency verification online before repeating it offline.
`runtimeSbom` describes the core artifact with zero runtime dependency
components. JUnit is test-only and must not enter that SBOM. Source, test
report, publication, bytecode, and `jdeps` validators are bounded and fail
closed.

Do not weaken dependency verification, replace immutable action SHAs with tags,
restore the removed unauthenticated GUI validation overload, re-enable a
current-JVM fallback, or add locale or streamer mode to mutation metadata as a
compatibility shortcut. See [SUPPLY_CHAIN.md](SUPPLY_CHAIN.md) for rollback
and evidence requirements.
