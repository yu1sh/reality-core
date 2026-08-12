package io.github.yu1sh.reality;

import io.github.yu1sh.reality.error.ErrorCode;
import io.github.yu1sh.reality.error.ErrorInfo;
import io.github.yu1sh.reality.error.Result;
import org.junit.jupiter.api.Test;

import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class ErrorResultTest {
    @Test
    void stableCodeHasLocalizableMessageKeyAndRedactedParameters() {
        ErrorInfo error = ErrorInfo.of(ErrorCode.REVISION_CONFLICT,
                Map.of("expectedVersion", "5", "currentVersion", "6"));

        assertEquals("revision_conflict", error.code().code());
        assertEquals("error.revision_conflict", error.messageKey());
        assertEquals("5", error.parameters().get("expectedVersion"));
        assertFalse(error.toString().contains("expectedVersion=5"));
        assertThrows(UnsupportedOperationException.class,
                () -> error.parameters().put("new", "value"));
    }

    @Test
    void resultSeparatesSuccessAndFailure() {
        Result<String> success = Result.success("ok");
        Result<String> failure = Result.failure(ErrorInfo.of(ErrorCode.MALFORMED_REQUEST));

        assertTrue(success.isSuccess());
        assertEquals("ok", success.value());
        assertEquals("OK", success.map(String::toUpperCase).value());
        assertTrue(failure.isFailure());
        assertEquals(ErrorCode.MALFORMED_REQUEST, failure.error().code());
        assertThrows(Exception.class, failure::value);
        assertThrows(Exception.class, success::error);
    }
}
