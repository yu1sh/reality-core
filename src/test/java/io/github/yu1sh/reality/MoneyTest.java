package io.github.yu1sh.reality;

import io.github.yu1sh.reality.money.CurrencyCode;
import io.github.yu1sh.reality.money.CurrencyMismatchException;
import io.github.yu1sh.reality.money.Money;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class MoneyTest {
    private static final CurrencyCode CREDITS = CurrencyCode.of("CRD");
    private static final CurrencyCode TOKENS = CurrencyCode.of("TOK");

    @Test
    void currencyCodeAcceptsBoundaryAndRejectsAmbiguousForms() {
        assertEquals("CRD", CREDITS.value());
        assertEquals("ABCDEFGH", CurrencyCode.of("ABCDEFGH").value());
        assertThrows(IllegalArgumentException.class, () -> CurrencyCode.of("crd"));
        assertThrows(IllegalArgumentException.class, () -> CurrencyCode.of("AB"));
        assertThrows(IllegalArgumentException.class, () -> CurrencyCode.of("ABCDEFGHI"));
        assertThrows(IllegalArgumentException.class, () -> CurrencyCode.of("CR D"));
    }

    @Test
    void usesMinorUnitsAndSupportsSameCurrencyArithmetic() {
        Money wallet = Money.ofMinorUnits(CREDITS, 125L);
        Money fee = Money.ofMinorUnits(CREDITS, 25L);

        assertEquals(150L, wallet.add(fee).minorUnits());
        assertEquals(100L, wallet.subtract(fee).minorUnits());
        assertEquals(375L, wallet.multiply(3L).minorUnits());
        assertEquals(-125L, wallet.negate().minorUnits());
        assertTrue(wallet.compareTo(fee) > 0);
        assertEquals(Money.zero(CREDITS), Money.ofMinorUnits(CREDITS, 0L));
    }

    @Test
    void refusesMixedCurrenciesAndOverflow() {
        Money credits = Money.ofMinorUnits(CREDITS, 10L);
        Money tokens = Money.ofMinorUnits(TOKENS, 10L);

        assertThrows(CurrencyMismatchException.class, () -> credits.add(tokens));
        assertThrows(CurrencyMismatchException.class, () -> credits.subtract(tokens));
        assertThrows(CurrencyMismatchException.class, () -> credits.compareTo(tokens));
        assertThrows(ArithmeticException.class, () -> Money.ofMinorUnits(CREDITS, Long.MAX_VALUE).add(credits));
        assertThrows(ArithmeticException.class, () -> Money.ofMinorUnits(CREDITS, Long.MAX_VALUE).multiply(2L));
        assertThrows(ArithmeticException.class, () -> Money.ofMinorUnits(CREDITS, Long.MIN_VALUE).negate());
    }
}
