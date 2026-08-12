package io.github.yu1sh.reality.transaction;

import io.github.yu1sh.reality.error.Result;

/** Work executed inside a transaction boundary owned by an adapter. */
@FunctionalInterface
public interface TransactionWork<T> {
    Result<T> run();
}
