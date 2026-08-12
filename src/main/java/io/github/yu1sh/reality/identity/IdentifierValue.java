package io.github.yu1sh.reality.identity;

import java.util.regex.Pattern;

final class IdentifierValue {
    private static final Pattern FORM = Pattern.compile("[A-Za-z0-9][A-Za-z0-9._:-]{0,127}");

    private IdentifierValue() {
    }

    static String require(String type, String value) {
        if (value == null || value.isBlank() || !FORM.matcher(value).matches()) {
            throw new IllegalArgumentException(type + " must be 1-128 ASCII identifier characters");
        }
        return value;
    }

    static String redacted(Class<?> type) {
        return type.getSimpleName() + "[redacted]";
    }
}
