package io.github.yu1sh.reality.identity;

import java.util.Objects;

/** Opaque identifier for a server-authorized GUI session. */
public final class SessionId {
    private final String value;

    private SessionId(String value) {
        this.value = IdentifierValue.require("SessionId", value);
    }

    public static SessionId of(String value) {
        return new SessionId(value);
    }

    public String value() {
        return value;
    }

    @Override
    public boolean equals(Object other) {
        return other instanceof SessionId that && value.equals(that.value);
    }

    @Override
    public int hashCode() {
        return Objects.hash(value);
    }

    /** Does not expose the session value in logs. */
    @Override
    public String toString() {
        return IdentifierValue.redacted(SessionId.class);
    }
}
