package io.github.yu1sh.reality.identity;

import java.util.Objects;

/** Opaque identity of the resource or aggregate affected by an operation. */
public final class SubjectId {
    private final String value;

    private SubjectId(String value) {
        this.value = IdentifierValue.require("SubjectId", value);
    }

    public static SubjectId of(String value) {
        return new SubjectId(value);
    }

    public String value() {
        return value;
    }

    @Override
    public boolean equals(Object other) {
        return other instanceof SubjectId that && value.equals(that.value);
    }

    @Override
    public int hashCode() {
        return Objects.hash(value);
    }

    /** Does not expose the subject value in logs. */
    @Override
    public String toString() {
        return IdentifierValue.redacted(SubjectId.class);
    }
}
