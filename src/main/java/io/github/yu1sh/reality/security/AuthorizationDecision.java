package io.github.yu1sh.reality.security;

import io.github.yu1sh.reality.error.ErrorCode;
import io.github.yu1sh.reality.error.ErrorInfo;
import io.github.yu1sh.reality.error.Result;

import java.util.Map;
import java.util.Objects;

/** Server-side allow/deny result that maps denial to a stable error code. */
public final class AuthorizationDecision {
    private final boolean allowed;
    private final ErrorInfo denial;

    private AuthorizationDecision(boolean allowed, ErrorInfo denial) {
        this.allowed = allowed;
        this.denial = denial;
    }

    public static AuthorizationDecision allowed() {
        return new AuthorizationDecision(true, null);
    }

    public static AuthorizationDecision denied() {
        return new AuthorizationDecision(false, ErrorInfo.of(ErrorCode.PERMISSION_DENIED));
    }

    public static AuthorizationDecision denied(Permission permission) {
        Objects.requireNonNull(permission, "permission");
        return new AuthorizationDecision(false, ErrorInfo.of(
                ErrorCode.PERMISSION_DENIED, Map.of("permission", permission.value())));
    }

    public boolean isAllowed() {
        return allowed;
    }

    public Result<Void> asResult() {
        return allowed ? Result.success() : Result.failure(denial);
    }

    public ErrorInfo denial() {
        if (allowed) {
            throw new IllegalStateException("Allowed decision has no denial");
        }
        return denial;
    }
}
