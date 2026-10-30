from __future__ import annotations

from datetime import datetime, timedelta
import unittest
from zoneinfo import ZoneInfo

from src.models import NormalizedBid, SourceRef
from src.run_egp import _display_candidate, _normalize_deadline_precision


KAMPALA = ZoneInfo("Africa/Kampala")


def make_bid(*, now: datetime, deadline_offset: timedelta, status: str = "open", published_offset: timedelta = timedelta(days=-1), deadline_precision: str = "datetime") -> NormalizedBid:
    return NormalizedBid(
        title="Supply of network equipment",
        organization="Test Procuring Entity",
        reference_number="TEST/SUPLS/2026-2027/001",
        published_at=now + published_offset,
        deadline_at=now + deadline_offset,
        deadline_precision=deadline_precision,
        status=status,
        sources=[
            SourceRef(
                name="eGP Uganda",
                url="https://egpuganda.go.ug/bid-notices/test",
                detected_at=now,
            )
        ],
    )


class TestLiveBidValidation(unittest.TestCase):
    def setUp(self) -> None:
        self.now = datetime(2026, 10, 30, 9, 0, tzinfo=KAMPALA)

    def test_active_future_bid_is_accepted(self):
        accepted, reason = _display_candidate(
            make_bid(now=self.now, deadline_offset=timedelta(days=5)),
            self.now,
        )
        self.assertTrue(accepted)
        self.assertEqual(reason, "verified-active")

    def test_deadline_that_has_passed_is_rejected(self):
        accepted, reason = _display_candidate(
            make_bid(now=self.now, deadline_offset=timedelta(seconds=-1)),
            self.now,
        )
        self.assertFalse(accepted)
        self.assertEqual(reason, "deadline-passed")

    def test_terminal_lifecycle_state_is_rejected_even_with_future_deadline(self):
        accepted, reason = _display_candidate(
            make_bid(now=self.now, deadline_offset=timedelta(days=5), status="evaluation"),
            self.now,
        )
        self.assertFalse(accepted)
        self.assertEqual(reason, "terminal-status:evaluation")

    def test_publication_after_deadline_is_rejected(self):
        accepted, reason = _display_candidate(
            make_bid(
                now=self.now,
                deadline_offset=timedelta(days=2),
                published_offset=timedelta(days=3),
            ),
            self.now,
        )
        self.assertFalse(accepted)
        self.assertEqual(reason, "publication-after-deadline")

    def test_implausibly_distant_deadline_is_rejected(self):
        accepted, reason = _display_candidate(
            make_bid(now=self.now, deadline_offset=timedelta(days=91)),
            self.now,
        )
        self.assertFalse(accepted)
        self.assertEqual(reason, "deadline-outside-live-window")

    def test_date_only_deadline_remains_open_for_full_closing_day(self):
        bid = make_bid(
            now=self.now,
            deadline_offset=timedelta(hours=-9),
            deadline_precision="date",
        )
        normalized = _normalize_deadline_precision(bid)
        self.assertEqual(normalized.deadline_at.hour, 23)
        self.assertEqual(normalized.deadline_at.minute, 59)
        accepted, reason = _display_candidate(normalized, self.now)
        self.assertTrue(accepted)
        self.assertEqual(reason, "verified-active")


if __name__ == "__main__":
    unittest.main()
