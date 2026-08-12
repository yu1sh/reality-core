package io.github.yu1sh.reality.gui;

import io.github.yu1sh.reality.identity.SessionId;
import io.github.yu1sh.reality.version.Revision;

import java.util.Map;
import java.util.Objects;

/**
 * Immutable point-in-time GUI data; field meaning belongs to the adapter.
 * Locale and streamer mode are server-issued presentation state, not mutation
 * request inputs.
 */
public final class GuiSnapshot {
    private final SessionId sessionId;
    private final Revision revision;
    private final LocaleTag locale;
    private final boolean streamerMode;
    private final Map<String, String> values;

    private GuiSnapshot(
            SessionId sessionId,
            Revision revision,
            LocaleTag locale,
            boolean streamerMode,
            Map<String, String> values) {
        this.sessionId = Objects.requireNonNull(sessionId, "sessionId");
        this.revision = Objects.requireNonNull(revision, "revision");
        this.locale = Objects.requireNonNull(locale, "locale");
        this.streamerMode = streamerMode;
        this.values = GuiFieldValidation.copyValues(values);
    }

    public static GuiSnapshot of(
            SessionId sessionId,
            Revision revision,
            LocaleTag locale,
            boolean streamerMode,
            Map<String, String> values) {
        return new GuiSnapshot(sessionId, revision, locale, streamerMode, values);
    }

    public SessionId sessionId() {
        return sessionId;
    }

    public Revision revision() {
        return revision;
    }

    public LocaleTag locale() {
        return locale;
    }

    public boolean streamerMode() {
        return streamerMode;
    }

    public Map<String, String> values() {
        return values;
    }

    @Override
    public String toString() {
        return "GuiSnapshot[revision=" + revision + ", locale=" + locale
                + ", streamerMode=" + streamerMode + ", fieldCount=" + values.size() + "]";
    }
}
