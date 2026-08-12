package io.github.yu1sh.reality.version;

import java.util.Objects;

/** Version of an event payload schema, independent from API and release versions. */
public final class SchemaVersion implements Comparable<SchemaVersion> {
    private final int value;

    private SchemaVersion(int value) {
        if (value < 1) {
            throw new IllegalArgumentException("SchemaVersion must be positive");
        }
        this.value = value;
    }

    public static SchemaVersion initial() {
        return new SchemaVersion(1);
    }

    public static SchemaVersion of(int value) {
        return new SchemaVersion(value);
    }

    public int value() {
        return value;
    }

    public SchemaVersion next() {
        return new SchemaVersion(Math.incrementExact(value));
    }

    @Override
    public int compareTo(SchemaVersion other) {
        return Integer.compare(value, Objects.requireNonNull(other, "other").value);
    }

    @Override
    public boolean equals(Object other) {
        return other instanceof SchemaVersion that && value == that.value;
    }

    @Override
    public int hashCode() {
        return Integer.hashCode(value);
    }

    @Override
    public String toString() {
        return Integer.toString(value);
    }
}
