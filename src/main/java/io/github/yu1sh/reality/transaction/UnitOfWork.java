package io.github.yu1sh.reality.transaction;

import io.github.yu1sh.reality.error.Result;

/**
 * Minimal transaction port. The core defines no database, connection, retry,
 * or migration implementation; the owning adapter supplies those semantics.
 */
public interface UnitOfWork {
    <T> Result<T> execute(TransactionWork<T> work);
}
