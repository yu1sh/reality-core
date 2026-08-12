package io.github.yu1sh.reality;

import io.github.yu1sh.reality.error.Result;
import io.github.yu1sh.reality.event.DomainEvent;
import io.github.yu1sh.reality.event.DomainEventEnvelope;
import io.github.yu1sh.reality.event.EventType;
import io.github.yu1sh.reality.gui.GuiSession;
import io.github.yu1sh.reality.gui.LocaleTag;
import io.github.yu1sh.reality.identity.ActorId;
import io.github.yu1sh.reality.identity.CorrelationId;
import io.github.yu1sh.reality.identity.EventId;
import io.github.yu1sh.reality.identity.OperationId;
import io.github.yu1sh.reality.identity.RequestId;
import io.github.yu1sh.reality.identity.SessionId;
import io.github.yu1sh.reality.identity.SubjectId;
import io.github.yu1sh.reality.mutation.MutationRequestMetadata;
import io.github.yu1sh.reality.security.AuthorizationDecision;
import io.github.yu1sh.reality.security.AuthorizationPort;
import io.github.yu1sh.reality.security.Permission;
import io.github.yu1sh.reality.transaction.TransactionWork;
import io.github.yu1sh.reality.transaction.UnitOfWork;
import io.github.yu1sh.reality.version.Revision;
import io.github.yu1sh.reality.version.SchemaVersion;
import org.junit.jupiter.api.Test;

import java.time.Instant;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

/** Cross-contract JVM integration test; no Minecraft runtime is involved. */
class CoreContractIntegrationTest {
    @Test
    void validatedMutationCanCarryOneCorrelationChainIntoAnAuditEnvelope() {
        Instant now = Instant.parse("2026-03-04T05:06:07Z");
        ActorId actor = ActorId.of("player-7");
        SessionId sessionId = SessionId.of("session-7");
        RequestId requestId = RequestId.of("request-7");
        OperationId operationId = OperationId.of("operation-7");
        CorrelationId correlationId = CorrelationId.of("correlation-7");
        SubjectId subject = SubjectId.of("wallet-7");
        GuiSession session = GuiSession.open(sessionId, actor, LocaleTag.of("en-US"), false,
                now.plusSeconds(30), Revision.initial());
        MutationRequestMetadata metadata = MutationRequestMetadata.of(
                requestId, operationId, sessionId, Revision.initial());
        AuthorizationPort authorization = (candidate, target, permission) -> AuthorizationDecision.allowed();
        UnitOfWork unitOfWork = new UnitOfWork() {
            @Override
            public <T> Result<T> execute(TransactionWork<T> work) {
                return work.run();
            }
        };

        assertTrue(session.validate(metadata, actor, now).isSuccess());
        assertTrue(authorization.authorize(actor, subject, Permission.of("wallet.credit")).isAllowed());
        Result<String> committed = unitOfWork.execute(() -> Result.success(operationId.value()));
        DomainEventEnvelope<BalanceChanged> event = DomainEventEnvelope.of(
                EventId.of("event-7"), requestId, operationId, actor, subject, correlationId,
                now, SchemaVersion.initial(), new BalanceChanged());

        assertEquals(operationId.value(), committed.value());
        assertEquals(requestId, event.requestId());
        assertEquals(operationId, event.operationId());
        assertEquals(actor, event.actor());
        assertEquals(subject, event.subject());
        assertEquals(correlationId, event.correlationId());
    }

    private record BalanceChanged() implements DomainEvent {
        @Override
        public EventType eventType() {
            return EventType.of("wallet.balance_changed");
        }
    }
}
