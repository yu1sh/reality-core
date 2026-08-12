package io.github.yu1sh.reality.error;

import java.util.NoSuchElementException;
import java.util.Objects;
import java.util.function.Function;

/** Explicit success/failure result used by ports and validation contracts. */
public final class Result<T> {
    private final T value;
    private final ErrorInfo error;

    private Result(T value, ErrorInfo error) {
        this.value = value;
        this.error = error;
    }

    public static <T> Result<T> success(T value) {
        return new Result<>(value, null);
    }

    public static Result<Void> success() {
        return new Result<>(null, null);
    }

    public static <T> Result<T> failure(ErrorInfo error) {
        return new Result<>(null, Objects.requireNonNull(error, "error"));
    }

    public boolean isSuccess() {
        return error == null;
    }

    public boolean isFailure() {
        return error != null;
    }

    public T value() {
        if (isFailure()) {
            throw new NoSuchElementException("Result has no value for " + error.code().code());
        }
        return value;
    }

    public ErrorInfo error() {
        if (isSuccess()) {
            throw new NoSuchElementException("Successful Result has no error");
        }
        return error;
    }

    public T orElseThrow() {
        if (isFailure()) {
            throw new IllegalStateException(error.code().code());
        }
        return value;
    }

    public <U> Result<U> map(Function<? super T, ? extends U> mapper) {
        Objects.requireNonNull(mapper, "mapper");
        if (isFailure()) {
            return Result.failure(error);
        }
        return Result.success(mapper.apply(value));
    }
}
