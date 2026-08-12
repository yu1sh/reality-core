package io.github.yu1sh.reality;

import io.github.yu1sh.reality.error.ErrorCode;
import io.github.yu1sh.reality.gui.GuiDelta;
import io.github.yu1sh.reality.gui.GuiSession;
import io.github.yu1sh.reality.gui.GuiSnapshot;
import io.github.yu1sh.reality.gui.LocaleTag;
import io.github.yu1sh.reality.identity.ActorId;
import io.github.yu1sh.reality.identity.OperationId;
import io.github.yu1sh.reality.identity.RequestId;
import io.github.yu1sh.reality.identity.SessionId;
import io.github.yu1sh.reality.mutation.MutationRequestMetadata;
import io.github.yu1sh.reality.version.Revision;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Modifier;
import java.time.Instant;
import java.util.Arrays;
import java.util.Map;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class GuiContractTest {
    private static final SessionId SESSION = SessionId.of("session-1");
    private static final ActorId ACTOR = ActorId.of("player-1");
    private static final ActorId OTHER_ACTOR = ActorId.of("player-2");
    private static final LocaleTag JAPANESE = LocaleTag.of("ja-JP");
    private static final LocaleTag ENGLISH = LocaleTag.of("en-US");
    private static final Instant NOW = Instant.parse("2026-02-03T04:05:06Z");

    @Test
    void sessionValidatesRequiredMutationMetadataAndDistinguishesFailures() {
        GuiSession session = GuiSession.open(SESSION, ACTOR, JAPANESE, true,
                NOW.plusSeconds(60), Revision.of(4));
        MutationRequestMetadata valid = request(SESSION, Revision.of(4));

        assertTrue(session.validate(valid, ACTOR, NOW).isSuccess());
        assertEquals(ErrorCode.MALFORMED_REQUEST,
                session.validate(null, ACTOR, NOW).error().code());
        assertEquals(ErrorCode.MALFORMED_REQUEST,
                session.validate(valid, null, NOW).error().code());
        assertEquals(ErrorCode.MALFORMED_REQUEST,
                session.validate(valid, ACTOR, null).error().code());
        assertEquals(ErrorCode.SESSION_EXPIRED,
                session.validate(valid, ACTOR, NOW.plusSeconds(60)).error().code());
        assertEquals(ErrorCode.INVALID_SESSION,
                session.validate(valid, OTHER_ACTOR, NOW).error().code());
        assertEquals(ErrorCode.REVISION_CONFLICT,
                session.validate(request(SESSION, Revision.of(3)), ACTOR, NOW).error().code());
        assertEquals(ErrorCode.INVALID_SESSION,
                session.validate(request(SessionId.of("other-session"), Revision.of(4)), ACTOR, NOW)
                        .error().code());

        assertEquals(RequestId.of("req-1"), valid.requestId());
        assertEquals(OperationId.of("operation-1"), valid.operationId());
        assertEquals(SESSION, valid.sessionId());
        assertEquals(Revision.of(4), valid.expectedVersion());
    }

    @Test
    void sessionSnapshotAndDeltaCarryServerIssuedPresentationStateWithoutScreenImplementation() {
        GuiSession session = GuiSession.open(SESSION, ACTOR, JAPANESE, true,
                NOW.plusSeconds(60), Revision.of(4));
        GuiSnapshot snapshot = GuiSnapshot.of(SESSION, Revision.of(4), JAPANESE, true,
                Map.of("wallet.balance", "100", "shop.open", "true"));
        GuiDelta delta = GuiDelta.of(SESSION, Revision.of(4), Revision.of(6), JAPANESE, true,
                Map.of("wallet.balance", "120"), Set.of("shop.open"));
        GuiSession englishSession = GuiSession.open(SESSION, ACTOR, ENGLISH, false,
                NOW.plusSeconds(60), Revision.of(4));
        GuiSnapshot englishSnapshot = GuiSnapshot.of(SESSION, Revision.of(4), ENGLISH, false,
                Map.of("wallet.balance", "100"));
        GuiDelta englishDelta = GuiDelta.of(SESSION, Revision.of(4), Revision.of(5), ENGLISH, false,
                Map.of("wallet.balance", "110"), Set.of());

        assertEquals(JAPANESE, session.locale());
        assertTrue(session.streamerMode());
        assertEquals(Revision.of(4), snapshot.revision());
        assertEquals(JAPANESE, snapshot.locale());
        assertTrue(snapshot.streamerMode());
        assertEquals("100", snapshot.values().get("wallet.balance"));
        assertEquals(Revision.of(6), delta.revision());
        assertEquals(JAPANESE, delta.locale());
        assertEquals(Set.of("shop.open"), delta.removedKeys());
        assertTrue(delta.streamerMode());
        assertEquals(ENGLISH, englishSession.locale());
        assertFalse(englishSession.streamerMode());
        assertEquals(ENGLISH, englishSnapshot.locale());
        assertFalse(englishSnapshot.streamerMode());
        assertEquals(ENGLISH, englishDelta.locale());
        assertFalse(englishDelta.streamerMode());
        assertThrows(UnsupportedOperationException.class,
                () -> snapshot.values().put("new.field", "value"));
        assertThrows(IllegalArgumentException.class,
                () -> GuiDelta.of(SESSION, Revision.of(4), Revision.of(4), JAPANESE, false,
                        Map.of(), Set.of()));
        assertThrows(IllegalArgumentException.class,
                () -> GuiDelta.of(SESSION, Revision.of(4), Revision.of(5), JAPANESE, false,
                        Map.of("wallet.balance", "120"), Set.of("wallet.balance")));
    }

    @Test
    void mutationMetadataHasNoPresentationStateInItsPublicApi() throws Exception {
        assertFalse(Arrays.stream(MutationRequestMetadata.class.getMethods())
                .anyMatch(method -> method.getName().equals("locale")
                        || method.getName().equals("streamerMode")));
        assertFalse(Arrays.stream(MutationRequestMetadata.class.getDeclaredFields())
                .anyMatch(field -> field.getName().equals("locale")
                        || field.getName().equals("streamerMode")));
        assertEquals(4, MutationRequestMetadata.class.getMethod("of",
                RequestId.class, OperationId.class, SessionId.class, Revision.class)
                .getParameterCount());
        assertFalse(Arrays.stream(MutationRequestMetadata.class.getConstructors())
                .anyMatch(constructor -> Modifier.isPublic(constructor.getModifiers())));
        assertEquals(3, GuiSession.class.getMethod("validate",
                MutationRequestMetadata.class, ActorId.class, Instant.class)
                .getParameterCount());
        assertThrows(NoSuchMethodException.class,
                () -> GuiSession.class.getMethod("validate", MutationRequestMetadata.class, Instant.class));
    }

    @Test
    void mutationMetadataRejectsNullRequiredFields() {
        assertThrows(NullPointerException.class,
                () -> MutationRequestMetadata.of(null, OperationId.of("operation-1"), SESSION,
                        Revision.initial()));
        assertThrows(NullPointerException.class,
                () -> MutationRequestMetadata.of(RequestId.of("req-1"), null, SESSION,
                        Revision.initial()));
        assertThrows(NullPointerException.class,
                () -> MutationRequestMetadata.of(RequestId.of("req-1"), OperationId.of("operation-1"),
                        null, Revision.initial()));
        assertThrows(NullPointerException.class,
                () -> MutationRequestMetadata.of(RequestId.of("req-1"), OperationId.of("operation-1"),
                        SESSION, null));
    }

    @Test
    void actorAndSessionOpaqueValuesNeverAppearInValidationDiagnostics() {
        GuiSession session = GuiSession.open(SESSION, ACTOR, ENGLISH, false,
                NOW.plusSeconds(60), Revision.of(4));
        var actorFailure = session.validate(request(SESSION, Revision.of(4)), OTHER_ACTOR, NOW);
        var sessionFailure = session.validate(
                request(SessionId.of("other-session"), Revision.of(4)), ACTOR, NOW);
        var revisionFailure = session.validate(request(SESSION, Revision.of(3)), ACTOR, NOW);

        assertFalse(session.toString().contains(ACTOR.value()));
        assertFalse(session.toString().contains(SESSION.value()));
        MutationRequestMetadata metadata = request(SESSION, Revision.of(4));
        assertFalse(metadata.toString().contains(ACTOR.value()));
        assertFalse(metadata.toString().contains(SESSION.value()));
        assertFalse(actorFailure.error().toString().contains(ACTOR.value()));
        assertFalse(actorFailure.error().toString().contains(SESSION.value()));
        assertFalse(sessionFailure.error().toString().contains(ACTOR.value()));
        assertFalse(sessionFailure.error().toString().contains(SESSION.value()));
        assertFalse(revisionFailure.error().toString().contains(ACTOR.value()));
        assertFalse(revisionFailure.error().toString().contains(SESSION.value()));
        assertTrue(revisionFailure.error().parameters().values().stream()
                .noneMatch(value -> value.contains(ACTOR.value()) || value.contains(SESSION.value())));
    }

    @Test
    void localeAndFieldKeysRejectMalformedInput() {
        assertEquals("en-US", ENGLISH.value());
        assertThrows(IllegalArgumentException.class, () -> LocaleTag.of("en_US"));
        assertThrows(IllegalArgumentException.class, () -> LocaleTag.of("日本語"));
        assertThrows(IllegalArgumentException.class,
                () -> GuiSnapshot.of(SESSION, Revision.initial(), JAPANESE, false,
                        Map.of("bad key", "value")));
    }

    private static MutationRequestMetadata request(SessionId sessionId, Revision expectedVersion) {
        return MutationRequestMetadata.of(
                RequestId.of("req-1"),
                OperationId.of("operation-1"),
                sessionId,
                expectedVersion);
    }
}
