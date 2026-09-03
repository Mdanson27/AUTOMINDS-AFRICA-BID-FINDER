from __future__ import annotations

from datetime import datetime, timedelta
import unittest
from zoneinfo import ZoneInfo

from src.export_live_snapshot import MAX_DAYS_AHEAD, is_eligible_bid, record_from_bid
from src.models import NormalizedBid, SourceRef
from src.sources.common_web import clean


KAMPALA = ZoneInfo("Africa/Kampala")
NOW = datetime(2026, 9, 3, 14, 30, tzinfo=KAMPALA)


def make_bid(
    *,
    deadline: datetime | None,
    published: datetime | None = datetime(2026, 8, 20, 9, 0, tzinfo=KAMPALA),
    status: str = "open",
    title: str = "Supply of ICT equipment",
    description: str = "Standard notice",
):
    return NormalizedBid(
        title=title,
        organization="Test Entity",
        reference_number="TEST/SUPLS/2026-2027/001",
        description=description,
        category="Supplies",
        procurement_type="Tender",
        published_at=published,
        deadline_at=deadline,
        deadline_precision="datetime" if deadline else "unknown",
        status=status,
        sources=[
            SourceRef(
                name="Test Source",
                url="https://example.com/tender",
                detected_at=NOW,
            )
        ],
    )


class BidQualityTests(unittest.TestCase):
    def test_clean_removes_html_and_entities(self):
        raw = "<p><strong>Invitation&nbsp;for Bids</strong></p><p>Supply &amp; installation</p>"
        self.assertEqual(clean(raw), "Invitation for Bids Supply & installation")

    def test_keeps_current_financial_year_bid_due_within_90_days(self):
        bid = make_bid(deadline=NOW + timedelta(days=20))
        self.assertTrue(is_eligible_bid(bid, NOW))

    def test_keeps_recent_closed_bid_from_current_financial_year(self):
        bid = make_bid(
            deadline=datetime(2026, 8, 15, 17, 0, tzinfo=KAMPALA),
            published=datetime(2026, 7, 12, 9, 0, tzinfo=KAMPALA),
            status="closed",
        )
        self.assertTrue(is_eligible_bid(bid, NOW))

    def test_rejects_pre_financial_year_bid(self):
        bid = make_bid(
            deadline=datetime(2026, 6, 30, 17, 0, tzinfo=KAMPALA),
            published=datetime(2026, 6, 1, 9, 0, tzinfo=KAMPALA),
            status="closed",
        )
        self.assertFalse(is_eligible_bid(bid, NOW))

    def test_rejects_bid_published_before_current_financial_year(self):
        bid = make_bid(
            deadline=NOW + timedelta(days=10),
            published=datetime(2026, 6, 30, 9, 0, tzinfo=KAMPALA),
        )
        self.assertFalse(is_eligible_bid(bid, NOW))

    def test_rejects_bid_more_than_90_days_away(self):
        bid = make_bid(deadline=NOW + timedelta(days=MAX_DAYS_AHEAD + 1))
        self.assertFalse(is_eligible_bid(bid, NOW))

    def test_rejects_missing_deadline(self):
        self.assertFalse(is_eligible_bid(make_bid(deadline=None), NOW))

    def test_rejects_cancelled_and_awarded_notices(self):
        deadline = NOW + timedelta(days=10)
        self.assertFalse(is_eligible_bid(make_bid(deadline=deadline, status="cancelled"), NOW))
        self.assertFalse(is_eligible_bid(make_bid(deadline=deadline, status="awarded"), NOW))

    def test_record_output_is_plain_text(self):
        bid = make_bid(
            deadline=NOW + timedelta(days=10),
            title="<p><strong>Supply&nbsp;of laptops</strong></p>",
            description="<div>Deliver &amp; install&nbsp;equipment</div>",
        )
        record = record_from_bid(bid, "2026-09-03T11:30:00Z", NOW)
        self.assertEqual(record["title"], "Supply of laptops")
        self.assertEqual(record["description"], "Deliver & install equipment")
        self.assertNotIn("<", record["title"])
        self.assertNotIn("&nbsp;", record["description"])


if __name__ == "__main__":
    unittest.main()
