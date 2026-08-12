# Compatibility and versioning

`reality-core` keeps four version concepts separate:

- **Artifact/API SemVer:** the Gradle project version (`0.1.0-SNAPSHOT`). A
  public type removal, incompatible signature change, or changed invariant is
  a breaking API change and requires a major version once the project is
  stable.
- **Event schema version:** `SchemaVersion` is carried in each
  `DomainEventEnvelope`. A payload change that cannot be read by existing
  consumers gets a new schema version and an adapter migration strategy.
- **Network protocol version:** owned by the Forge/platform transport. It is
  not inferred from the artifact version or event schema version.
- **Database migration version:** owned by a persistence implementation. Core
  declares no migrations or migration number.

Before a breaking public API change, maintainers should:

1. add a replacement API and document the migration;
2. deprecate the old API for at least one compatible release where practical;
3. remove it only in the next permitted SemVer breaking release; and
4. update examples, tests, changelog, and downstream adapter contracts.

Stable error-code strings, event type strings, identifier validation, and
currency arithmetic rules are compatibility surface. Adding a new error code
or event schema is not permission to reinterpret an existing code or schema.

## Pre-public GUI contract migration

The `0.1.0-SNAPSHOT` GUI contract is pre-public, so the following hardening is
an intentional source/API break rather than a deprecated compatibility layer:

- Replace `MutationRequestMetadata.of(requestId, operationId, sessionId,
  expectedVersion, locale, streamerMode)` with the four-argument factory that
  ends at `expectedVersion`.
- Replace `session.validate(metadata, now)` with
  `session.validate(metadata, authenticatedActor, now)`, where
  `authenticatedActor` is obtained from the server's connection/authentication
  boundary.
- Read locale and streamer mode from the server-issued `GuiSession`,
  `GuiSnapshot`, or `GuiDelta`. A mutation packet is not a presentation-state
  update boundary.

The removed overloads must not be retained for compatibility because they
permit mutation validation without a server-authenticated actor. No database
migration is required. The starting commit
`3eb2e9b6c0583bc3190bb69c29a0e6d503e92a87` can be used only for local recovery;
it is not an acceptable formal rollback because it predates this security
hardening.

## Public hardening compatibility

The supply-chain gate, runtime SBOM, source scanner, and GitHub metadata added
for public readiness do not change Java packages, public signatures, error
codes, identifier semantics, event contracts, transaction ports, or GUI
presentation ownership. No Java API migration or database migration is
required. A rollback must not restore the removed unauthenticated validation
overload or client-controlled locale/streamer mutation fields.
