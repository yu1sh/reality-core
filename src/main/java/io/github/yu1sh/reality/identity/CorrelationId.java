package io.github.yu1sh.reality.identity;

import java.util.Objects;

/** Opaque identifier used to connect requests, operations and emitted events. */
public final class CorrelationId {
    private final String value;

    private CorrelationId(String value) {
        this.value = IdentifierValue.require("CorrelationId", value);
    }

    public static CorrelationId of(String value) {
        return new CorrelationId(value);
    }

    public String value() {
        return value;
    }

    @Override
    public boolean equals(Object other) {
        return other instanceof CorrelationId that && value.equals(that.value);
    }

    @Override
    public int hashCode() {
        return Objects.hash(value);
    }

    /** Does not expose the correlation value in logs. */
    @Override
    public String toString() {
        return IdentifierValue.redacted(CorrelationId.class);
    }
}
