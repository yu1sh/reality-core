package io.github.yu1sh.reality.event;

import java.util.Objects;
import java.util.regex.Pattern;

/** Stable, lower-case domain event type name. */
public final class EventType {
    private static final Pattern FORM = Pattern.compile("[a-z][a-z0-9_.-]{1,95}");
    private final String value;

    private EventType(String value) {
        if (value == null || !FORM.matcher(value).matches()) {
            throw new IllegalArgumentException("EventType must be 2-96 lower-case ASCII characters");
        }
        this.value = value;
    }

    public static EventType of(String value) {
        return new EventType(value);
    }

    public String value() {
        return value;
    }

    @Override
    public boolean equals(Object other) {
        return other instanceof EventType that && value.equals(that.value);
    }

    @Override
    public int hashCode() {
        return Objects.hash(value);
    }

    @Override
    public String toString() {
        return value;
    }
}
