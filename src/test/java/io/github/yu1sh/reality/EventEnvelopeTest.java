package io.github.yu1sh.reality;

import io.github.yu1sh.reality.event.DomainEvent;
import io.github.yu1sh.reality.event.DomainEventEnvelope;
import io.github.yu1sh.reality.event.EventType;
import io.github.yu1sh.reality.identity.ActorId;
import io.github.yu1sh.reality.identity.CorrelationId;
import io.github.yu1sh.reality.identity.EventId;
import io.github.yu1sh.reality.identity.OperationId;
import io.github.yu1sh.reality.identity.RequestId;
import io.github.yu1sh.reality.identity.SubjectId;
import io.github.yu1sh.reality.version.SchemaVersion;
import org.junit.jupiter.api.Test;

import java.time.Instant;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

class EventEnvelopeTest {
    private static final EventType TYPE = EventType.of("wallet.credited");

    @Test
    void envelopeCarriesAuditAndCorrelationMetadata() {
        Instant occurredAt = Instant.parse("2026-01-02T03:04:05Z");
        SampleEvent payload = new SampleEvent(TYPE, 25L);
        DomainEventEnvelope<SampleEvent> envelope = DomainEventEnvelope.of(
                EventId.of("evt-1"),
                RequestId.of("req-1"),
                OperationId.of("op-1"),
                ActorId.of("player-1"),
                SubjectId.of("wallet-1"),
                CorrelationId.of("corr-1"),
                occurredAt,
                SchemaVersion.of(3),
                payload);

        assertEquals(TYPE, envelope.eventType());
        assertEquals(payload, envelope.payload());
        assertEquals(ActorId.of("player-1"), envelope.actor());
        assertEquals(SubjectId.of("wallet-1"), envelope.subject());
        assertEquals(CorrelationId.of("corr-1"), envelope.correlationId());
        assertEquals(OperationId.of("op-1"), envelope.operationId());
        assertEquals(occurredAt, envelope.occurredAt());
        assertEquals(3, envelope.schemaVersion().value());
    }

    @Test
    void eventTypeAndRequiredEnvelopeFieldsAreValidated() {
        assertThrows(IllegalArgumentException.class, () -> EventType.of("Wallet.Credited"));
        assertThrows(IllegalArgumentException.class, () -> EventType.of("x"));
        assertThrows(NullPointerException.class, () -> DomainEventEnvelope.of(
                EventId.of("evt-1"), RequestId.of("req-1"), OperationId.of("op-1"),
                ActorId.of("player-1"), SubjectId.of("wallet-1"), CorrelationId.of("corr-1"),
                Instant.now(), SchemaVersion.initial(), null));
    }

    private record SampleEvent(EventType eventType, long amount) implements DomainEvent {
    }
}
