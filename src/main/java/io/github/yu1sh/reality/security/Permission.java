package io.github.yu1sh.reality.security;

import java.util.Objects;
import java.util.regex.Pattern;

/** Stable permission name evaluated on the server. */
public final class Permission {
    private static final Pattern FORM = Pattern.compile("[a-z][a-z0-9_.:-]{1,127}");
    private final String value;

    private Permission(String value) {
        if (value == null || !FORM.matcher(value).matches()) {
            throw new IllegalArgumentException("Permission must be 2-128 lower-case ASCII characters");
        }
        this.value = value;
    }

    public static Permission of(String value) {
        return new Permission(value);
    }

    public String value() {
        return value;
    }

    @Override
    public boolean equals(Object other) {
        return other instanceof Permission that && value.equals(that.value);
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
