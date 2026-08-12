package io.github.yu1sh.reality.event;

/**
 * Marker contract for immutable event payloads. The payload type and schema
 * are owned by the feature or adapter that defines the event.
 */
public interface DomainEvent {
    EventType eventType();
}
