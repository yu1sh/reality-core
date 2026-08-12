package io.github.yu1sh.reality.gui;

import java.util.Objects;
import java.util.regex.Pattern;

/** BCP-47-shaped locale tag used for adapter-side localization. */
public final class LocaleTag {
    private static final Pattern FORM = Pattern.compile("[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8}){0,3}");
    private final String value;

    private LocaleTag(String value) {
        if (value == null || value.length() > 35 || !FORM.matcher(value).matches()) {
            throw new IllegalArgumentException("LocaleTag must be a valid hyphenated locale tag");
        }
        this.value = value;
    }

    public static LocaleTag of(String value) {
        return new LocaleTag(value);
    }

    public String value() {
        return value;
    }

    @Override
    public boolean equals(Object other) {
        return other instanceof LocaleTag that && value.equals(that.value);
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
