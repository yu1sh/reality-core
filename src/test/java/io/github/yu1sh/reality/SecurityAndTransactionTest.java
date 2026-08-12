package io.github.yu1sh.reality;

import io.github.yu1sh.reality.error.ErrorCode;
import io.github.yu1sh.reality.error.Result;
import io.github.yu1sh.reality.identity.ActorId;
import io.github.yu1sh.reality.identity.SubjectId;
import io.github.yu1sh.reality.security.AuthorizationDecision;
import io.github.yu1sh.reality.security.AuthorizationPort;
import io.github.yu1sh.reality.security.Permission;
import io.github.yu1sh.reality.security.PermissionSet;
import io.github.yu1sh.reality.transaction.UnitOfWork;
import org.junit.jupiter.api.Test;

import java.util.Set;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

class SecurityAndTransactionTest {
    @Test
    void authorizationDenialIsStableAndPermissionSetIsImmutable() {
        Permission purchase = Permission.of("shop.purchase");
        PermissionSet permissions = PermissionSet.of(Set.of(purchase));
        AuthorizationPort authorizer = (actor, subject, required) ->
                permissions.contains(required) ? AuthorizationDecision.allowed() : AuthorizationDecision.denied(required);

        assertTrue(authorizer.authorize(ActorId.of("player"), SubjectId.of("shop"), purchase).asResult().isSuccess());
        Result<Void> denied = authorizer.authorize(
                ActorId.of("player"), SubjectId.of("bank"), Permission.of("bank.withdraw")).asResult();
        assertTrue(denied.isFailure());
        assertEquals(ErrorCode.PERMISSION_DENIED, denied.error().code());
        assertFalse(permissions.contains(Permission.of("bank.withdraw")));
        assertThrows(UnsupportedOperationException.class,
                () -> permissions.permissions().add(Permission.of("admin")));
        assertThrows(IllegalArgumentException.class, () -> Permission.of("bad permission"));
    }

    @Test
    void unitOfWorkIsTheOnlyTransactionContract() {
        UnitOfWork unitOfWork = new UnitOfWork() {
            @Override
            public <T> Result<T> execute(io.github.yu1sh.reality.transaction.TransactionWork<T> work) {
                return work.run();
            }
        };
        Result<String> result = unitOfWork.execute(() -> Result.success("committed"));

        assertEquals("committed", result.value());
    }
}
