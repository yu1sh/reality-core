package io.github.yu1sh.reality;

import io.github.yu1sh.reality.identity.ActorId;
import io.github.yu1sh.reality.identity.CorrelationId;
import io.github.yu1sh.reality.identity.EventId;
import io.github.yu1sh.reality.identity.OperationId;
import io.github.yu1sh.reality.identity.RequestId;
import io.github.yu1sh.reality.identity.SessionId;
import io.github.yu1sh.reality.identity.SubjectId;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;

import java.util.function.Function;
import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;

class IdentityValueTest {
    private static Stream<Arguments> identifierFactories() {
        return Stream.of(
                Arguments.of((Function<String, Object>) RequestId::of),
                Arguments.of((Function<String, Object>) OperationId::of),
                Arguments.of((Function<String, Object>) CorrelationId::of),
                Arguments.of((Function<String, Object>) SessionId::of),
                Arguments.of((Function<String, Object>) ActorId::of),
                Arguments.of((Function<String, Object>) SubjectId::of),
                Arguments.of((Function<String, Object>) EventId::of));
    }

    @ParameterizedTest
    @MethodSource("identifierFactories")
    void acceptsValidBoundaryFormAndRedactsToString(Function<String, Object> factory) {
        String value = "a" + "x".repeat(127);
        Object identifier = factory.apply(value);

        assertNotEquals(value, identifier.toString());
        assertEquals(identifier, factory.apply(value));
        assertThrows(IllegalArgumentException.class, () -> factory.apply(""));
        assertThrows(IllegalArgumentException.class, () -> factory.apply("has whitespace"));
        assertThrows(IllegalArgumentException.class, () -> factory.apply("bad/slash"));
        assertThrows(IllegalArgumentException.class, () -> factory.apply("x".repeat(129)));
        assertThrows(IllegalArgumentException.class, () -> factory.apply("\nnewline"));
    }
}
