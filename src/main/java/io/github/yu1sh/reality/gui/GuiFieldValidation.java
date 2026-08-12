package io.github.yu1sh.reality.gui;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.regex.Pattern;

final class GuiFieldValidation {
    private static final Pattern KEY_FORM = Pattern.compile("[A-Za-z][A-Za-z0-9_.:-]{0,127}");

    private GuiFieldValidation() {
    }

    static Map<String, String> copyValues(Map<String, String> values) {
        Objects.requireNonNull(values, "values");
        if (values.size() > 512) {
            throw new IllegalArgumentException("GUI payload supports at most 512 fields");
        }
        Map<String, String> copy = new LinkedHashMap<>();
        values.forEach((key, value) -> {
            requireKey(key);
            if (value == null || value.length() > 8192) {
                throw new IllegalArgumentException("GUI field value is invalid");
            }
            copy.put(key, value);
        });
        return Map.copyOf(copy);
    }

    static Set<String> copyKeys(Set<String> keys) {
        Objects.requireNonNull(keys, "keys");
        if (keys.size() > 512) {
            throw new IllegalArgumentException("GUI payload supports at most 512 fields");
        }
        keys.forEach(GuiFieldValidation::requireKey);
        return Set.copyOf(keys);
    }

    static void requireKey(String key) {
        if (key == null || !KEY_FORM.matcher(key).matches()) {
            throw new IllegalArgumentException("GUI field key is invalid");
        }
    }
}
