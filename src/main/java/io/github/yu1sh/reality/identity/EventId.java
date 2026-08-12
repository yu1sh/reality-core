package io.github.yu1sh.reality.identity;

import java.util.Objects;

/** Opaque identifier for an emitted domain event. */
public final class EventId {
    private final String value;

    private EventId(String value) {
        this.value = IdentifierValue.require("EventId", value);
    }

    public static EventId of(String value) {
        return new EventId(value);
    }

    public String value() {
        return value;
    }

    @Override
    public boolean equals(Object other) {
        return other instanceof EventId that && value.equals(that.value);
    }

    @Override
    public int hashCode() {
        return Objects.hash(value);
    }

    /** Does not expose the event value in logs. */
    @Override
    public String toString() {
        return IdentifierValue.redacted(EventId.class);
    }
}
