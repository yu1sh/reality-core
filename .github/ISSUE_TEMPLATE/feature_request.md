---
name: Feature request
about: Propose a narrowly scoped, Minecraft-independent core change.
title: "[Feature] "
labels: enhancement
assignees: ''
---

## Problem and proposed contract

<!-- Describe the shared adapter/feature need without adding a feature service. -->

## API signature impact

- Proposed public types/methods:
- Why the existing contract is insufficient:
- Confirm whether `MutationRequestMetadata` remains four-field:
- Confirm whether `GuiSession.validate(metadata, authenticatedActor, now)` remains authenticated-actor required:

## Server authority and presentation state

- Server-authenticated actor source:
- Locale/streamer presentation source (`GuiSession`, `GuiSnapshot`, or `GuiDelta`):
- Why this cannot be a client mutation input:

## Migration, rollback, and verification

- Source/API migration:
- Database migration (normally none in core):
- Safe rollback plan that does not restore unsafe validation:
- Required unit/property/integration evidence:
- SBOM, source-scan, reproducibility, or action-pin impact:

## Scope

- [ ] No Minecraft/Forge/DB/network codec/GUI Screen implementation is proposed.
- [ ] No dynamic dependency, binary, secret, or local absolute path is proposed.
