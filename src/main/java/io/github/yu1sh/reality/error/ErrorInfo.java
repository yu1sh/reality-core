package io.github.yu1sh.reality.error;

import java.util.LinkedHashMap;
import java.util.Map;
import java.util.Objects;

/**
 * Structured failure data. Only a message key and parameters are carried so
 * adapters can localize the message without embedding Japanese or English in
 * the core contract.
 */
public final class ErrorInfo {
    private final ErrorCode code;
    private final Map<String, String> parameters;
    private final boolean retryable;

    private ErrorInfo(ErrorCode code, Map<String, String> parameters, boolean retryable) {
        this.code = Objects.requireNonNull(code, "code");
        this.parameters = copyParameters(parameters);
        this.retryable = retryable;
    }

    public static ErrorInfo of(ErrorCode code) {
        return new ErrorInfo(code, Map.of(), code.retryableByDefault());
    }

    public static ErrorInfo of(ErrorCode code, Map<String, String> parameters) {
        return new ErrorInfo(code, parameters, code.retryableByDefault());
    }

    public static ErrorInfo of(ErrorCode code, Map<String, String> parameters, boolean retryable) {
        return new ErrorInfo(code, parameters, retryable);
    }

    public ErrorCode code() {
        return code;
    }

    public String messageKey() {
        return code.messageKey();
    }

    public Map<String, String> parameters() {
        return parameters;
    }

    public boolean retryable() {
        return retryable;
    }

    private static Map<String, String> copyParameters(Map<String, String> source) {
        Objects.requireNonNull(source, "parameters");
        if (source.size() > 64) {
            throw new IllegalArgumentException("ErrorInfo supports at most 64 parameters");
        }
        Map<String, String> copy = new LinkedHashMap<>();
        source.forEach((key, value) -> {
            if (key == null || key.isBlank() || key.length() > 64 || value == null || value.length() > 1024) {
                throw new IllegalArgumentException("ErrorInfo parameter key/value is invalid");
            }
            copy.put(key, value);
        });
        return Map.copyOf(copy);
    }

    /** Parameter values are intentionally omitted to keep logs free of secrets. */
    @Override
    public String toString() {
        return "ErrorInfo[code=" + code.code() + ", parameterCount=" + parameters.size()
                + ", retryable=" + retryable + "]";
    }
}
