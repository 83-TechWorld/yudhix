"""Unit tests for the SaaS layer: billing math, slugs, invitations, token claims, permissions."""
import os
import sys
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.platform import billing  # noqa: E402
from app.platform.auth import AuthError, Membership, principal_from_claims  # noqa: E402
from app.platform.workspaces import hash_token, is_expired, slugify  # noqa: E402

UTC = timezone.utc


class BillingMathTest(unittest.TestCase):
    def test_month_and_year_intervals_clamp_to_month_end(self):
        self.assertEqual(billing.add_interval(datetime(2026, 1, 31, tzinfo=UTC), "MONTH"), datetime(2026, 2, 28, tzinfo=UTC))
        self.assertEqual(billing.add_interval(datetime(2026, 11, 2, tzinfo=UTC), "MONTH"), datetime(2026, 12, 2, tzinfo=UTC))
        self.assertEqual(billing.add_interval(datetime(2026, 12, 15, tzinfo=UTC), "MONTH"), datetime(2027, 1, 15, tzinfo=UTC))
        self.assertEqual(billing.add_interval(datetime(2028, 2, 29, tzinfo=UTC), "YEAR"), datetime(2029, 2, 28, tzinfo=UTC))

    def test_gst_for_india_only(self):
        self.assertEqual(billing.tax_for("IN_GST_18", Decimal("99")), (Decimal("17.82"), "GST 18%"))
        self.assertEqual(billing.tax_for("US_STATE_TAX", Decimal("99"))[0], Decimal("0.00"))

    def test_proration_credit_for_unused_half(self):
        p = billing.Period(datetime(2026, 11, 1, tzinfo=UTC), datetime(2026, 12, 1, tzinfo=UTC))
        self.assertEqual(billing.proration_credit(Decimal("100"), p, datetime(2026, 11, 16, tzinfo=UTC)), Decimal("50.00"))
        self.assertEqual(billing.proration_credit(Decimal("100"), p, datetime(2026, 12, 5, tzinfo=UTC)), Decimal("0.00"))

    def test_comment_overage(self):
        plan = {"comment_quota": 10000}
        self.assertEqual(billing.overage_lines({"COMMENT_INGESTED": 9000}, plan), [])
        line = billing.overage_lines({"COMMENT_INGESTED": 12500}, plan)[0]
        self.assertEqual(line["amount"], Decimal("5.00"))  # 2.5 x $2 per 1,000
        self.assertEqual(billing.overage_lines({"COMMENT_INGESTED": 10 ** 7}, {"comment_quota": -1}), [])

    def test_trial_expiry(self):
        now = datetime(2026, 11, 2, tzinfo=UTC)
        self.assertEqual(billing.effective_status({"status": "TRIALING", "trial_ends_at": now + timedelta(days=1)}, now), "TRIALING")
        self.assertEqual(billing.effective_status({"status": "TRIALING", "trial_ends_at": now - timedelta(seconds=1)}, now), "TRIAL_EXPIRED")
        self.assertEqual(billing.effective_status({"status": "ACTIVE", "trial_ends_at": None}, now), "ACTIVE")


class WorkspaceHelpersTest(unittest.TestCase):
    def test_slugify(self):
        self.assertEqual(slugify("Sony Interactive Entertainment"), "sony-interactive-entertainment")
        self.assertEqual(slugify("  Café Noir & Co. "), "cafe-noir-co")
        self.assertEqual(slugify("!!!"), "workspace")
        self.assertLessEqual(len(slugify("x" * 200)), 48)

    def test_invite_tokens_are_hashed_and_expire(self):
        self.assertEqual(len(hash_token("abc")), 64)
        self.assertNotEqual(hash_token("abc"), "abc")
        now = datetime(2026, 11, 2, tzinfo=UTC)
        self.assertTrue(is_expired(now - timedelta(seconds=1), now))
        self.assertFalse(is_expired(now + timedelta(days=7), now))


class TokenClaimsTest(unittest.TestCase):
    BASE = {"sub": "u1", "azp": "yudhix-web", "typ": "Bearer", "email": "Asha@Example.com", "email_verified": True,
            "given_name": "Asha", "family_name": "Rao"}

    def test_valid_claims(self):
        p = principal_from_claims(dict(self.BASE))
        self.assertEqual((p.sub, p.email, p.name, p.email_verified), ("u1", "asha@example.com", "Asha Rao", True))

    def test_other_client_rejected(self):
        with self.assertRaises(AuthError):
            principal_from_claims({**self.BASE, "azp": "some-other-app"})

    def test_id_token_and_missing_email_rejected(self):
        with self.assertRaises(AuthError):
            principal_from_claims({**self.BASE, "typ": "ID"})
        with self.assertRaises(AuthError):
            principal_from_claims({**self.BASE, "email": ""})


class PermissionsTest(unittest.TestCase):
    def m(self, role):
        return Membership("t", "Acme", "u", role, "a@b.c", "A")

    def test_matrix(self):
        self.assertTrue(self.m("admin").can("billing.manage"))
        self.assertFalse(self.m("approver").can("team.manage"))
        self.assertTrue(self.m("approver").can("reply.approve"))
        self.assertTrue(self.m("agent").can("content.write"))
        self.assertFalse(self.m("agent").can("reply.approve"))
        for p in ("content.write", "reply.approve", "team.manage", "billing.manage", "workspace.manage"):
            self.assertFalse(self.m("analyst").can(p), p)


if __name__ == "__main__":
    unittest.main()
