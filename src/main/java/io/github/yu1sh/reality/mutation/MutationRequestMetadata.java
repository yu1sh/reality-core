package io.github.yu1sh.reality.mutation;

import io.github.yu1sh.reality.identity.OperationId;
import io.github.yu1sh.reality.identity.RequestId;
import io.github.yu1sh.reality.identity.SessionId;
import io.github.yu1sh.reality.version.Revision;

import java.util.Objects;

/**
 * Required metadata for every mutation request.
 *
 * <p>This is transport metadata only. It deliberately contains no presentation
 * state: locale and streamer mode are server-issued fields of {@code
 * GuiSession}, {@code GuiSnapshot}, and {@code GuiDelta}. A client cannot
 * change those values by sending a mutation packet. {@code operationId} is the
 * idempotency key and must not be replaced by the per-attempt {@code requestId}.
 */
public final class MutationRequestMetadata {
    private final RequestId requestId;
    private final OperationId operationId;
    private final SessionId sessionId;
    private final Revision expectedVersion;

    private MutationRequestMetadata(
            RequestId requestId,
            OperationId operationId,
            SessionId sessionId,
            Revision expectedVersion) {
        this.requestId = Objects.requireNonNull(requestId, "requestId");
        this.operationId = Objects.requireNonNull(operationId, "operationId");
        this.sessionId = Objects.requireNonNull(sessionId, "sessionId");
        this.expectedVersion = Objects.requireNonNull(expectedVersion, "expectedVersion");
    }

    /**
     * Creates the four required fields for a mutation request.
     *
     * @param requestId identifier for this delivery attempt
     * @param operationId idempotency key for the logical operation
     * @param sessionId server-issued GUI session referenced by the request
     * @param expectedVersion revision observed by the client
     * @return immutable mutation metadata
     * @throws NullPointerException if any required field is {@code null}
     */
    public static MutationRequestMetadata of(
            RequestId requestId,
            OperationId operationId,
            SessionId sessionId,
            Revision expectedVersion) {
        return new MutationRequestMetadata(requestId, operationId, sessionId, expectedVersion);
    }

    public RequestId requestId() {
        return requestId;
    }

    public OperationId operationId() {
        return operationId;
    }

    public SessionId sessionId() {
        return sessionId;
    }

    public Revision expectedVersion() {
        return expectedVersion;
    }

    /**
     * Does not expose opaque request, operation, or session values in logs;
     * their value objects provide redacted string forms.
     */
    @Override
    public String toString() {
        return "MutationRequestMetadata[requestId=" + requestId
                + ", operationId=" + operationId + ", sessionId=" + sessionId
                + ", expectedVersion=" + expectedVersion + "]";
    }
}
