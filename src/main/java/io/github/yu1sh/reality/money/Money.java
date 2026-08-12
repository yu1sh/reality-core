package io.github.yu1sh.reality.money;

import java.util.Objects;

/**
 * Immutable money amount represented only in minor units. No floating-point
 * operation is available, and arithmetic rejects mixed currencies.
 */
public final class Money implements Comparable<Money> {
    private final CurrencyCode currency;
    private final long minorUnits;

    private Money(CurrencyCode currency, long minorUnits) {
        this.currency = Objects.requireNonNull(currency, "currency");
        this.minorUnits = minorUnits;
    }

    public static Money ofMinorUnits(CurrencyCode currency, long minorUnits) {
        return new Money(currency, minorUnits);
    }

    public static Money zero(CurrencyCode currency) {
        return ofMinorUnits(currency, 0L);
    }

    public CurrencyCode currency() {
        return currency;
    }

    public long minorUnits() {
        return minorUnits;
    }

    public boolean isZero() {
        return minorUnits == 0L;
    }

    public boolean isNegative() {
        return minorUnits < 0L;
    }

    public Money add(Money other) {
        requireSameCurrency(other);
        return new Money(currency, Math.addExact(minorUnits, other.minorUnits));
    }

    public Money subtract(Money other) {
        requireSameCurrency(other);
        return new Money(currency, Math.subtractExact(minorUnits, other.minorUnits));
    }

    public Money multiply(long multiplier) {
        return new Money(currency, Math.multiplyExact(minorUnits, multiplier));
    }

    public Money negate() {
        return new Money(currency, Math.negateExact(minorUnits));
    }

    @Override
    public int compareTo(Money other) {
        requireSameCurrency(other);
        return Long.compare(minorUnits, other.minorUnits);
    }

    private void requireSameCurrency(Money other) {
        Objects.requireNonNull(other, "other");
        if (!currency.equals(other.currency)) {
            throw new CurrencyMismatchException(currency, other.currency);
        }
    }

    @Override
    public boolean equals(Object other) {
        return other instanceof Money that
                && minorUnits == that.minorUnits
                && currency.equals(that.currency);
    }

    @Override
    public int hashCode() {
        return Objects.hash(currency, minorUnits);
    }

    @Override
    public String toString() {
        return "Money[currency=" + currency + ", minorUnits=" + minorUnits + "]";
    }
}
