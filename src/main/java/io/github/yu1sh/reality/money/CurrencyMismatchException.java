package io.github.yu1sh.reality.money;

/** Raised when an arithmetic operation combines different currencies. */
public final class CurrencyMismatchException extends IllegalArgumentException {
    public CurrencyMismatchException(CurrencyCode left, CurrencyCode right) {
        super("Money currencies must match: " + left.value() + " and " + right.value());
    }
}
