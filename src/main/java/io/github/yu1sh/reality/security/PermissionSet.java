package io.github.yu1sh.reality.security;

import java.util.Collections;
import java.util.HashSet;
import java.util.Objects;
import java.util.Set;

/** Immutable server-side set of permissions. */
public final class PermissionSet {
    private final Set<Permission> permissions;

    private PermissionSet(Set<Permission> permissions) {
        Objects.requireNonNull(permissions, "permissions");
        if (permissions.stream().anyMatch(Objects::isNull)) {
            throw new IllegalArgumentException("PermissionSet cannot contain null");
        }
        this.permissions = Collections.unmodifiableSet(new HashSet<>(permissions));
    }

    public static PermissionSet of(Set<Permission> permissions) {
        return new PermissionSet(permissions);
    }

    public static PermissionSet empty() {
        return new PermissionSet(Set.of());
    }

    public boolean contains(Permission permission) {
        return permissions.contains(Objects.requireNonNull(permission, "permission"));
    }

    public Set<Permission> permissions() {
        return permissions;
    }
}
