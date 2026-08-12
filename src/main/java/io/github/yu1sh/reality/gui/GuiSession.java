package io.github.yu1sh.reality.gui;

import io.github.yu1sh.reality.error.ErrorCode;
import io.github.yu1sh.reality.error.ErrorInfo;
import io.github.yu1sh.reality.error.Result;
import io.github.yu1sh.reality.identity.ActorId;
import io.github.yu1sh.reality.identity.SessionId;
import io.github.yu1sh.reality.mutation.MutationRequestMetadata;
import io.github.yu1sh.reality.version.Revision;

import java.time.Instant;
import java.util.Map;
import java.util.Objects;

/**
 * Minecraft-independent server-issued GUI session state. It is immutable;
 * adapters create a new value when the session revision or presentation state
 * is server-authorized to advance.
 *
 * <p>The actor, locale, and streamer mode are session state issued by the
 * server. Mutation metadata carries only the session and concurrency fields;
 * clients cannot override this presentation state in a mutation packet.
 */
public final class GuiSession {
    private final SessionId sessionId;
    private final ActorId actor;
    private final LocaleTag locale;
    private final boolean streamerMode;
    private final Instant expiresAt;
    private final Revision revision;

    private GuiSession(
            SessionId sessionId,
            ActorId actor,
            LocaleTag locale,
            boolean streamerMode,
            Instant expiresAt,
            Revision revision) {
        this.sessionId = Objects.requireNonNull(sessionId, "sessionId");
        this.actor = Objects.requireNonNull(actor, "actor");
        this.locale = Objects.requireNonNull(locale, "locale");
        this.streamerMode = streamerMode;
        this.expiresAt = Objects.requireNonNull(expiresAt, "expiresAt");
        this.revision = Objects.requireNonNull(revision, "revision");
    }

    public static GuiSession open(
            SessionId sessionId,
            ActorId actor,
            LocaleTag locale,
            boolean streamerMode,
            Instant expiresAt,
            Revision revision) {
        return new GuiSession(sessionId, actor, locale, streamerMode, expiresAt, revision);
    }

    public SessionId sessionId() {
        return sessionId;
    }

    public ActorId actor() {
        return actor;
    }

    public LocaleTag locale() {
        return locale;
    }

    public boolean streamerMode() {
        return streamerMode;
    }

    public Instant expiresAt() {
        return expiresAt;
    }

    public Revision revision() {
        return revision;
    }

    public boolean isExpired(Instant now) {
        return !Objects.requireNonNull(now, "now").isBefore(expiresAt);
    }

    /**
     * Performs server-side actor, session, expiry, and optimistic-concurrency
     * validation. The authenticated actor must come from the server-side
     * connection/authentication boundary; it must not be reconstructed from
     * client packet fields. A client cannot make an expired session, an actor
     * mismatch, or a stale expected version valid.
     *
     * @param request mutation metadata received from the client
     * @param authenticatedActor actor authenticated by the server for the
     *                           network connection handling this request
     * @param now server-side current time
     * @return success only when the actor, session, expiry, and revision all
     *         match this server-issued session
     */
    public Result<Void> validate(
            MutationRequestMetadata request,
            ActorId authenticatedActor,
            Instant now) {
        if (request == null || authenticatedActor == null || now == null) {
            return Result.failure(ErrorInfo.of(ErrorCode.MALFORMED_REQUEST));
        }
        if (!actor.equals(authenticatedActor)) {
            return Result.failure(ErrorInfo.of(ErrorCode.INVALID_SESSION));
        }
        if (!sessionId.equals(request.sessionId())) {
            return Result.failure(ErrorInfo.of(ErrorCode.INVALID_SESSION));
        }
        if (isExpired(now)) {
            return Result.failure(ErrorInfo.of(ErrorCode.SESSION_EXPIRED));
        }
        if (!revision.equals(request.expectedVersion())) {
            return Result.failure(ErrorInfo.of(ErrorCode.REVISION_CONFLICT, Map.of(
                    "expectedVersion", request.expectedVersion().toString(),
                    "currentVersion", revision.toString())));
        }
        return Result.success();
    }

    /** Does not expose session or actor identities in logs. */
    @Override
    public String toString() {
        return "GuiSession[locale=" + locale + ", streamerMode=" + streamerMode
                + ", expiresAt=" + expiresAt + ", revision=" + revision + "]";
    }
}
