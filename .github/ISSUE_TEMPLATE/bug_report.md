---
name: Bug report
about: Report a reproducible defect in the Minecraft-independent core contract.
title: "[Bug] "
labels: bug
assignees: ''
---

## Summary

<!-- What happened, and what did you expect? -->

## Reproduction and evidence

- Commit or artifact version:
- Exact command/test:
- Expected result:
- Actual result:

## API and GUI contract boundary

- `MutationRequestMetadata` signature involved (the public contract has exactly `requestId`, `operationId`, `sessionId`, and `expectedVersion`):
- `GuiSession.validate(metadata, authenticatedActor, now)` call involved:
- Was the actor server-authenticated at the connection boundary? If not, explain:
- Locale/streamer mode source (`GuiSession`, `GuiSnapshot`, or `GuiDelta`):

## Migration and rollback evidence

- Required source migration, if any:
- Safe rollback/recovery evidence:
- Confirm that no unsafe overload or client-controlled presentation input was restored:

## Scope

- [ ] No Minecraft/Forge/GUI Screen dependency is required to reproduce this.
- [ ] No secret, binary, or local absolute path is included in this report.
