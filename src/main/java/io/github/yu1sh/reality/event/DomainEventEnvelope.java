package io.github.yu1sh.reality.event;

import io.github.yu1sh.reality.identity.ActorId;
import io.github.yu1sh.reality.identity.CorrelationId;
import io.github.yu1sh.reality.identity.EventId;
import io.github.yu1sh.reality.identity.OperationId;
import io.github.yu1sh.reality.identity.RequestId;
import io.github.yu1sh.reality.identity.SubjectId;
import io.github.yu1sh.reality.version.SchemaVersion;

import java.time.Instant;
import java.util.Objects;

/**
 * Versioned, auditable event metadata shared by feature services and
 * persistence or transport adapters.
 *
 * @param <T> immutable event payload type
 */
public final class DomainEventEnvelope<T extends DomainEvent> {
    private final EventId eventId;
    private final RequestId requestId;
    private final OperationId operationId;
    private final ActorId actor;
    private final SubjectId subject;
    private final CorrelationId correlationId;
    private final Instant occurredAt;
    private final SchemaVersion schemaVersion;
    private final T payload;

    private DomainEventEnvelope(
            EventId eventId,
            RequestId requestId,
            OperationId operationId,
            ActorId actor,
            SubjectId subject,
            CorrelationId correlationId,
            Instant occurredAt,
            SchemaVersion schemaVersion,
            T payload) {
        this.eventId = Objects.requireNonNull(eventId, "eventId");
        this.requestId = Objects.requireNonNull(requestId, "requestId");
        this.operationId = Objects.requireNonNull(operationId, "operationId");
        this.actor = Objects.requireNonNull(actor, "actor");
        this.subject = Objects.requireNonNull(subject, "subject");
        this.correlationId = Objects.requireNonNull(correlationId, "correlationId");
        this.occurredAt = Objects.requireNonNull(occurredAt, "occurredAt");
        this.schemaVersion = Objects.requireNonNull(schemaVersion, "schemaVersion");
        this.payload = Objects.requireNonNull(payload, "payload");
        Objects.requireNonNull(payload.eventType(), "payload.eventType");
    }

    public static <T extends DomainEvent> DomainEventEnvelope<T> of(
            EventId eventId,
            RequestId requestId,
            OperationId operationId,
            ActorId actor,
            SubjectId subject,
            CorrelationId correlationId,
            Instant occurredAt,
            SchemaVersion schemaVersion,
            T payload) {
        return new DomainEventEnvelope<>(eventId, requestId, operationId, actor, subject,
                correlationId, occurredAt, schemaVersion, payload);
    }

    public EventId eventId() {
        return eventId;
    }

    public RequestId requestId() {
        return requestId;
    }

    public OperationId operationId() {
        return operationId;
    }

    public ActorId actor() {
        return actor;
    }

    public SubjectId subject() {
        return subject;
    }

    public CorrelationId correlationId() {
        return correlationId;
    }

    public Instant occurredAt() {
        return occurredAt;
    }

    public SchemaVersion schemaVersion() {
        return schemaVersion;
    }

    public T payload() {
        return payload;
    }

    public EventType eventType() {
        return payload.eventType();
    }
}
