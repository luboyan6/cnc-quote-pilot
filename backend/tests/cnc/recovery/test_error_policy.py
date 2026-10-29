import unittest
from datetime import UTC, datetime, timedelta

from app.modules.cnc.login.contracts import LoginError
from app.modules.cnc.recovery.contracts import (
    ErrorCategory,
    RecoveryAction,
    SideEffectState,
)
from app.modules.cnc.recovery.policy import (
    classify_error,
    sanitize_error_message,
)


class ErrorPolicyTests(unittest.TestCase):
    def setUp(self):
        self.fixed_now = datetime(2026, 10, 28, 12, 0, 0, tzinfo=UTC)

    def clock(self):
        return self.fixed_now

    def test_uncertain_side_effect_always_reconciling(self):
        # Even on network error, if effect_state is UNCERTAIN, do NOT auto-retry!
        decision = classify_error(
            error="NETWORK_TIMEOUT",
            stage="UPLOADING",
            effect_state=SideEffectState.UNCERTAIN,
            attempt_count=1,
            clock=self.clock,
        )
        self.assertEqual(decision.category, ErrorCategory.UNCERTAIN_MUTATION)
        self.assertEqual(decision.action, RecoveryAction.RECONCILING)
        self.assertFalse(decision.retryable)
        self.assertEqual(decision.error_code, "RECONCILIATION_REQUIRED")
        self.assertIsNone(decision.next_attempt_at)

    def test_human_action_required(self):
        for reason in ["WAITING_HUMAN", "CAPTCHA_REQUIRED", "MFA_REQUIRED", "DECLARATION_REQUIRED"]:
            decision = classify_error(
                error=reason,
                stage="RUNNING",
                effect_state=SideEffectState.NONE,
                attempt_count=1,
                clock=self.clock,
            )
            self.assertEqual(decision.category, ErrorCategory.HUMAN_ACTION_REQUIRED)
            self.assertEqual(decision.action, RecoveryAction.WAITING_HUMAN)
            self.assertFalse(decision.retryable)
            self.assertEqual(decision.error_code, "WAITING_HUMAN_REQUIRED")

    def test_claimed_mutation_timeout_requires_reconciliation(self):
        decision = classify_error("NETWORK_TIMEOUT", stage="UPLOADING", effect_state=SideEffectState.CLAIMED, clock=self.clock)
        self.assertEqual(decision.action, RecoveryAction.RECONCILING)
        self.assertFalse(decision.retryable)

    def test_session_expired_single_reauth_budget(self):
        # First session expiry: allow re-auth
        d1 = classify_error(
            error=LoginError("SESSION_EXPIRED"),
            stage="AUTHENTICATING",
            attempt_count=1,
            reauth_count=0,
            max_reauth=1,
            clock=self.clock,
        )
        self.assertEqual(d1.category, ErrorCategory.SESSION_EXPIRED)
        self.assertEqual(d1.action, RecoveryAction.REAUTHENTICATE)
        self.assertTrue(d1.retryable)

        # Subsequent session expiry: reauth budget exhausted -> FAIL_TERMINAL
        d2 = classify_error(
            error=LoginError("SESSION_EXPIRED"),
            stage="AUTHENTICATING",
            attempt_count=2,
            reauth_count=1,
            max_reauth=1,
            clock=self.clock,
        )
        self.assertEqual(d2.category, ErrorCategory.SESSION_EXPIRED)
        self.assertEqual(d2.action, RecoveryAction.FAIL_TERMINAL)
        self.assertFalse(d2.retryable)
        self.assertEqual(d2.error_code, "SESSION_EXPIRED_REAUTH_EXHAUSTED")

    def test_rate_limited_cooldown(self):
        d1 = classify_error(
            error="RATE_LIMITED",
            stage="RUNNING",
            attempt_count=1,
            max_attempts=3,
            cooldown_seconds=90,
            clock=self.clock,
        )
        self.assertEqual(d1.category, ErrorCategory.RATE_LIMITED)
        self.assertEqual(d1.action, RecoveryAction.RETRY_WAIT)
        self.assertTrue(d1.retryable)
        self.assertEqual(d1.next_attempt_at, self.fixed_now + timedelta(seconds=90))

        # When attempt budget is exhausted:
        d2 = classify_error(
            error="RATE_LIMITED",
            stage="RUNNING",
            attempt_count=3,
            max_attempts=3,
            clock=self.clock,
        )
        self.assertEqual(d2.action, RecoveryAction.FAIL_TERMINAL)
        self.assertFalse(d2.retryable)

    def test_temporary_network_backoff_and_exhaustion(self):
        # Attempt 1 -> Retry 1 (delay 30s)
        d1 = classify_error(
            error="NETWORK_TIMEOUT",
            attempt_count=1,
            max_attempts=3,
            clock=self.clock,
            jitter=0.0,
        )
        self.assertEqual(d1.action, RecoveryAction.RETRY_WAIT)
        self.assertTrue(d1.retryable)
        self.assertEqual(d1.next_attempt_at, self.fixed_now + timedelta(seconds=30))

        # Attempt 2 -> Retry 2 (delay 120s)
        d2 = classify_error(
            error="NETWORK_TIMEOUT",
            attempt_count=2,
            max_attempts=3,
            clock=self.clock,
            jitter=0.0,
        )
        self.assertEqual(d2.action, RecoveryAction.RETRY_WAIT)
        self.assertTrue(d2.retryable)
        self.assertEqual(d2.next_attempt_at, self.fixed_now + timedelta(seconds=120))

        # Attempt 3 -> Max attempts reached -> FAIL_TERMINAL
        d3 = classify_error(
            error="NETWORK_TIMEOUT",
            attempt_count=3,
            max_attempts=3,
            clock=self.clock,
        )
        self.assertEqual(d3.action, RecoveryAction.FAIL_TERMINAL)
        self.assertFalse(d3.retryable)
        self.assertEqual(d3.error_code, "MAX_ATTEMPTS_EXCEEDED")

    def test_dom_contract_changed(self):
        decision = classify_error(
            error="DOM_CHANGED",
            clock=self.clock,
        )
        self.assertEqual(decision.category, ErrorCategory.DOM_CONTRACT_CHANGED)
        self.assertEqual(decision.action, RecoveryAction.FAIL_TERMINAL)
        self.assertFalse(decision.retryable)

    def test_local_persistence_failed(self):
        decision = classify_error(
            error="LOCAL_PERSISTENCE_FAILED",
            clock=self.clock,
        )
        self.assertEqual(decision.category, ErrorCategory.LOCAL_PERSISTENCE_FAILED)
        self.assertEqual(decision.action, RecoveryAction.RETRY_LOCAL_SAVE)
        self.assertTrue(decision.retryable)

    def test_permanent_rejection(self):
        decision = classify_error(
            error="JLC_EFFECTIVE_PARAMETERS_UNVERIFIED",
            clock=self.clock,
        )
        self.assertEqual(decision.category, ErrorCategory.PERMANENT_REJECTED)
        self.assertEqual(decision.action, RecoveryAction.FAIL_TERMINAL)
        self.assertFalse(decision.retryable)
        self.assertEqual(decision.error_code, "JLC_EFFECTIVE_PARAMETERS_UNVERIFIED")

    def test_sanitize_error_message(self):
        raw = "Error at C:\\Users\\admin\\secret\\pwd.txt: password='123456' bearer abc.def.ghi. Traceback (most recent call last): line 1"
        sanitized = sanitize_error_message(raw)
        self.assertNotIn("password='123456'", sanitized)
        self.assertNotIn("C:\\Users\\admin", sanitized)
        self.assertNotIn("bearer abc.def.ghi", sanitized)
        self.assertNotIn("Traceback", sanitized)


if __name__ == "__main__":
    unittest.main()
