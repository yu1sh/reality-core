package io.github.yu1sh.reality.gui;

import io.github.yu1sh.reality.identity.SessionId;
import io.github.yu1sh.reality.version.Revision;

import java.util.Map;
import java.util.Objects;
import java.util.Set;

/**
 * Immutable GUI change set. A delta may coalesce several domain revisions but
 * must always move strictly forward from its base revision. Locale and
 * streamer mode are server-issued presentation state, not mutation request
 * inputs.
 */
public final class GuiDelta {
    private final SessionId sessionId;
    private final Revision fromRevision;
    private final Revision toRevision;
    private final LocaleTag locale;
    private final boolean streamerMode;
    private final Map<String, String> updatedValues;
    private final Set<String> removedKeys;

    private GuiDelta(
            SessionId sessionId,
            Revision fromRevision,
            Revision toRevision,
            LocaleTag locale,
            boolean streamerMode,
            Map<String, String> updatedValues,
            Set<String> removedKeys) {
        this.sessionId = Objects.requireNonNull(sessionId, "sessionId");
        this.fromRevision = Objects.requireNonNull(fromRevision, "fromRevision");
        this.toRevision = Objects.requireNonNull(toRevision, "toRevision");
        if (!toRevision.isAfter(fromRevision)) {
            throw new IllegalArgumentException("GuiDelta toRevision must be after fromRevision");
        }
        this.locale = Objects.requireNonNull(locale, "locale");
        this.streamerMode = streamerMode;
        this.updatedValues = GuiFieldValidation.copyValues(updatedValues);
        this.removedKeys = GuiFieldValidation.copyKeys(removedKeys);
        if (!java.util.Collections.disjoint(this.updatedValues.keySet(), this.removedKeys)) {
            throw new IllegalArgumentException("A GUI field cannot be updated and removed in one delta");
        }
    }

    public static GuiDelta of(
            SessionId sessionId,
            Revision fromRevision,
            Revision toRevision,
            LocaleTag locale,
            boolean streamerMode,
            Map<String, String> updatedValues,
            Set<String> removedKeys) {
        return new GuiDelta(sessionId, fromRevision, toRevision, locale, streamerMode,
                updatedValues, removedKeys);
    }

    public SessionId sessionId() {
        return sessionId;
    }

    public Revision fromRevision() {
        return fromRevision;
    }

    public Revision toRevision() {
        return toRevision;
    }

    public Revision revision() {
        return toRevision;
    }

    public LocaleTag locale() {
        return locale;
    }

    public boolean streamerMode() {
        return streamerMode;
    }

    public Map<String, String> updatedValues() {
        return updatedValues;
    }

    public Set<String> removedKeys() {
        return removedKeys;
    }

    @Override
    public String toString() {
        return "GuiDelta[fromRevision=" + fromRevision + ", toRevision=" + toRevision
                + ", locale=" + locale + ", streamerMode=" + streamerMode
                + ", updatedCount=" + updatedValues.size() + ", removedCount=" + removedKeys.size() + "]";
    }
}
