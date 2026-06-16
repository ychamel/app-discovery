"""Tests for magic-link issue/verify (T-07, DESIGN.md §4 concurrency, §8).

This is the risk-first task, so the edges are exercised hard: hash-only storage,
TTL, single-use, forged tokens, and a real concurrent double-spend.
"""

import threading
from datetime import timedelta
from urllib.parse import parse_qs, urlparse

from django.db import connection
from django.test import TestCase, TransactionTestCase
from django.utils import timezone

from apps.accounts.auth_backend import _hash_token, issue_login_link, verify_token
from apps.accounts.models import Account, LoginToken
from apps.core.email import EmailSendError

BASE_URL = "https://discover.test"


class _CapturingSender:
    """Records sends so tests can read the emitted link."""

    def __init__(self):
        self.sent = []

    def send(self, to, template, context):
        self.sent.append({"to": to, "template": template, "context": context})


class _FailingSender:
    def send(self, to, template, context):
        raise EmailSendError("transport down")


def _raw_token_from(sender: _CapturingSender) -> str:
    link = sender.sent[-1]["context"]["link"]
    return parse_qs(urlparse(link).query)["token"][0]


class IssueLoginLinkTests(TestCase):
    def setUp(self):
        self.account = Account.objects.create_account("u@example.com")

    def test_raw_token_is_never_persisted(self):
        sender = _CapturingSender()
        issue_login_link(self.account, "login", base_url=BASE_URL, email_sender=sender)
        raw = _raw_token_from(sender)
        # The stored hash matches the raw token, but the raw token itself appears nowhere.
        self.assertFalse(LoginToken.objects.filter(token_hash=raw).exists())
        self.assertTrue(LoginToken.objects.filter(token_hash=_hash_token(raw)).exists())

    def test_link_points_at_verify_path(self):
        sender = _CapturingSender()
        issue_login_link(self.account, "register", base_url=BASE_URL, email_sender=sender)
        link = sender.sent[-1]["context"]["link"]
        self.assertTrue(link.startswith(f"{BASE_URL}/auth/verify?token="))

    def test_expiry_is_ttl_in_the_future(self):
        sender = _CapturingSender()
        before = timezone.now()
        token = issue_login_link(self.account, "login", base_url=BASE_URL, email_sender=sender)
        self.assertGreater(token.expires_at, before)

    def test_send_failure_propagates(self):
        with self.assertRaises(EmailSendError):
            issue_login_link(
                self.account, "login", base_url=BASE_URL, email_sender=_FailingSender()
            )


class VerifyTokenTests(TestCase):
    def setUp(self):
        self.account = Account.objects.create_account("u@example.com")
        self.sender = _CapturingSender()

    def _issue(self):
        issue_login_link(self.account, "login", base_url=BASE_URL, email_sender=self.sender)
        return _raw_token_from(self.sender)

    def test_happy_path_returns_account_and_consumes(self):
        raw = self._issue()
        self.assertEqual(verify_token(raw), self.account)
        self.assertIsNotNone(LoginToken.objects.get().consumed_at)

    def test_expired_token_rejected(self):
        raw = self._issue()
        LoginToken.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertIsNone(verify_token(raw))

    def test_already_consumed_token_rejected(self):
        raw = self._issue()
        self.assertEqual(verify_token(raw), self.account)
        self.assertIsNone(verify_token(raw))  # second use denied

    def test_forged_token_rejected(self):
        self._issue()
        self.assertIsNone(verify_token("not-a-real-token"))


class ConcurrentVerifyTests(TransactionTestCase):
    """A token must be consumable exactly once even under simultaneous clicks."""

    reset_sequences = True

    def test_concurrent_double_spend_exactly_one_succeeds(self):
        account = Account.objects.create_account("race@example.com")
        sender = _CapturingSender()
        issue_login_link(account, "login", base_url=BASE_URL, email_sender=sender)
        raw = _raw_token_from(sender)

        results = []
        results_lock = threading.Lock()
        start = threading.Barrier(2)

        def worker():
            start.wait()  # maximize overlap of the two UPDATEs
            try:
                outcome = verify_token(raw)
                with results_lock:
                    results.append(outcome)
            finally:
                connection.close()  # release this thread's DB connection

        threads = [threading.Thread(target=worker) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        successes = [r for r in results if r is not None]
        self.assertEqual(len(successes), 1, f"expected exactly one success, got {results}")
        self.assertEqual(LoginToken.objects.filter(consumed_at__isnull=False).count(), 1)
