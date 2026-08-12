package io.github.yu1sh.reality.identity;

import java.util.Objects;

/** Opaque identity of the principal initiating an operation. */
public final class ActorId {
    private final String value;

    private ActorId(String value) {
        this.value = IdentifierValue.require("ActorId", value);
    }

    public static ActorId of(String value) {
        return new ActorId(value);
    }

    public String value() {
        return value;
    }

    @Override
    public boolean equals(Object other) {
        return other instanceof ActorId that && value.equals(that.value);
    }

    @Override
    public int hashCode() {
        return Objects.hash(value);
    }

    /** Does not expose the actor value in logs. */
    @Override
    public String toString() {
        return IdentifierValue.redacted(ActorId.class);
    }
}
