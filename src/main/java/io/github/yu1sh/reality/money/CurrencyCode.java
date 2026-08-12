package io.github.yu1sh.reality.money;

import java.util.Objects;
import java.util.regex.Pattern;

/**
 * Upper-case code for one currency. Codes are deliberately independent of
 * Minecraft item identifiers or database identifiers.
 */
public final class CurrencyCode {
    private static final Pattern FORM = Pattern.compile("[A-Z][A-Z0-9]{2,7}");
    private final String value;

    private CurrencyCode(String value) {
        if (value == null || !FORM.matcher(value).matches()) {
            throw new IllegalArgumentException("CurrencyCode must be 3-8 upper-case ASCII characters");
        }
        this.value = value;
    }

    public static CurrencyCode of(String value) {
        return new CurrencyCode(value);
    }

    public String value() {
        return value;
    }

    @Override
    public boolean equals(Object other) {
        return other instanceof CurrencyCode that && value.equals(that.value);
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
