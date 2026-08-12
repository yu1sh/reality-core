package io.github.yu1sh.reality;

import io.github.yu1sh.reality.identity.RequestId;
import io.github.yu1sh.reality.money.CurrencyCode;
import io.github.yu1sh.reality.money.Money;
import io.github.yu1sh.reality.version.Revision;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

/** Deterministic property-style coverage without an unpinned generator library. */
class DeterministicPropertyTest {
    @Test
    void revisionNextAlwaysAdvancesAcrossRepresentativeRange() {
        for (long value = 0L; value <= 10_000L; value++) {
            Revision current = Revision.of(value);
            assertTrue(current.next().isAfter(current));
            assertEquals(value + 1L, current.next().value());
        }
    }

    @Test
    void sameCurrencyAdditionIsCommutativeAcrossRepresentativeAmounts() {
        CurrencyCode currency = CurrencyCode.of("CRD");
        for (long left = -100L; left <= 100L; left++) {
            for (long right = -100L; right <= 100L; right++) {
                Money first = Money.ofMinorUnits(currency, left);
                Money second = Money.ofMinorUnits(currency, right);
                assertEquals(first.add(second), second.add(first));
            }
        }
    }

    @Test
    void validIdentifierRoundTripsWithoutChangingItsValue() {
        for (int index = 0; index < 100; index++) {
            String value = "request-" + index + ".v1";
            assertEquals(value, RequestId.of(value).value());
        }
    }
}
