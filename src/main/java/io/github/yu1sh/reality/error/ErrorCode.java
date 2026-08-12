package io.github.yu1sh.reality.error;

/** Stable machine-readable failure codes. The code string is the wire value. */
public enum ErrorCode {
    MALFORMED_REQUEST("malformed_request", "error.malformed_request", false),
    PERMISSION_DENIED("permission_denied", "error.permission_denied", false),
    INVALID_SESSION("invalid_session", "error.invalid_session", false),
    SESSION_EXPIRED("session_expired", "error.session_expired", false),
    REVISION_CONFLICT("revision_conflict", "error.revision_conflict", true),
    OPERATION_ALREADY_PROCESSED("operation_already_processed", "error.operation_already_processed", false),
    NOT_FOUND("not_found", "error.not_found", false),
    INVALID_ARGUMENT("invalid_argument", "error.invalid_argument", false),
    INSUFFICIENT_FUNDS("insufficient_funds", "error.insufficient_funds", false),
    UNSUPPORTED_OPERATION("unsupported_operation", "error.unsupported_operation", false),
    INVARIANT_VIOLATION("invariant_violation", "error.invariant_violation", false),
    INTERNAL_FAILURE("internal_failure", "error.internal_failure", true);

    private final String code;
    private final String messageKey;
    private final boolean retryableByDefault;

    ErrorCode(String code, String messageKey, boolean retryableByDefault) {
        this.code = code;
        this.messageKey = messageKey;
        this.retryableByDefault = retryableByDefault;
    }

    public String code() {
        return code;
    }

    public String messageKey() {
        return messageKey;
    }

    public boolean retryableByDefault() {
        return retryableByDefault;
    }

    @Override
    public String toString() {
        return code;
    }
}
