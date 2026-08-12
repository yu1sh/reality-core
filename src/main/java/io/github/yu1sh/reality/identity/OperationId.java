package io.github.yu1sh.reality.identity;

import java.util.Objects;

/** Idempotency key for one mutation operation; distinct from {@link RequestId}. */
public final class OperationId {
    private final String value;

    private OperationId(String value) {
        this.value = IdentifierValue.require("OperationId", value);
    }

    public static OperationId of(String value) {
        return new OperationId(value);
    }

    public String value() {
        return value;
    }

    @Override
    public boolean equals(Object other) {
        return other instanceof OperationId that && value.equals(that.value);
    }

    @Override
    public int hashCode() {
        return Objects.hash(value);
    }

    /** Does not expose the idempotency key in logs. */
    @Override
    public String toString() {
        return IdentifierValue.redacted(OperationId.class);
    }
}
