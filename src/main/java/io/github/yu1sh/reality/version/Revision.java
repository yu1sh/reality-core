package io.github.yu1sh.reality.version;

import java.util.Objects;

/** Immutable non-negative aggregate or GUI revision. */
public final class Revision implements Comparable<Revision> {
    private final long value;

    private Revision(long value) {
        if (value < 0L) {
            throw new IllegalArgumentException("Revision cannot be negative");
        }
        this.value = value;
    }

    public static Revision initial() {
        return new Revision(0L);
    }

    public static Revision of(long value) {
        return new Revision(value);
    }

    public long value() {
        return value;
    }

    /** Returns the only revision that directly follows this revision. */
    public Revision next() {
        return new Revision(Math.incrementExact(value));
    }

    public boolean isAfter(Revision other) {
        return compareTo(other) > 0;
    }

    public boolean isBefore(Revision other) {
        return compareTo(other) < 0;
    }

    @Override
    public int compareTo(Revision other) {
        return Long.compare(value, Objects.requireNonNull(other, "other").value);
    }

    @Override
    public boolean equals(Object other) {
        return other instanceof Revision that && value == that.value;
    }

    @Override
    public int hashCode() {
        return Long.hashCode(value);
    }

    @Override
    public String toString() {
        return Long.toString(value);
    }
}
