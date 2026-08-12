package io.github.yu1sh.reality.identity;

import java.util.Objects;

/** Opaque identifier for one client or adapter request. */
public final class RequestId {
    private final String value;

    private RequestId(String value) {
        this.value = IdentifierValue.require("RequestId", value);
    }

    public static RequestId of(String value) {
        return new RequestId(value);
    }

    public String value() {
        return value;
    }

    @Override
    public boolean equals(Object other) {
        return other instanceof RequestId that && value.equals(that.value);
    }

    @Override
    public int hashCode() {
        return Objects.hash(value);
    }

    /** Does not expose the opaque value in logs. */
    @Override
    public String toString() {
        return IdentifierValue.redacted(RequestId.class);
    }
}
