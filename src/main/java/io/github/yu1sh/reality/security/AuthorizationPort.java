package io.github.yu1sh.reality.security;

import io.github.yu1sh.reality.identity.ActorId;
import io.github.yu1sh.reality.identity.SubjectId;

/**
 * Minimal server-owned authorization boundary. A client-provided permission
 * claim must never be used as the implementation of this port.
 */
@FunctionalInterface
public interface AuthorizationPort {
    AuthorizationDecision authorize(ActorId actor, SubjectId subject, Permission permission);
}
