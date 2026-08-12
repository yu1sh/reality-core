package io.github.yu1sh.reality;

import io.github.yu1sh.reality.version.Revision;
import io.github.yu1sh.reality.version.SchemaVersion;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class VersionTest {
    @Test
    void revisionStartsAtZeroAndOnlyMovesForward() {
        Revision initial = Revision.initial();
        Revision next = initial.next();

        assertEquals(0L, initial.value());
        assertEquals(1L, next.value());
        assertTrue(next.isAfter(initial));
        assertTrue(initial.isBefore(next));
        assertThrows(IllegalArgumentException.class, () -> Revision.of(-1L));
        assertThrows(ArithmeticException.class, () -> Revision.of(Long.MAX_VALUE).next());
    }

    @Test
    void schemaVersionIsIndependentPositiveEventVersion() {
        SchemaVersion first = SchemaVersion.initial();
        assertEquals(1, first.value());
        assertEquals(2, first.next().value());
        assertThrows(IllegalArgumentException.class, () -> SchemaVersion.of(0));
        assertThrows(ArithmeticException.class, () -> SchemaVersion.of(Integer.MAX_VALUE).next());
    }
}
