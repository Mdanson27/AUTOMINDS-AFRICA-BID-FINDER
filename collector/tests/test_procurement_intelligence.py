from __future__ import annotations

from datetime import datetime, timedelta
import unittest
from zoneinfo import ZoneInfo

from src.export_live_snapshot import extract_intelligence, record_from_bid
from src.models import NormalizedBid, SourceRef


KAMPALA = ZoneInfo("Africa/Kampala")
NOW = datetime(2026, 9, 3, 14, 30, tzinfo=KAMPALA)


def make_bid(description: str):
    return NormalizedBid(
        title="Supply and installation of ICT equipment",
        organization="Example Procuring Entity",
        reference_number="EXAMPLE/SUPLS/2026-2027/001",
        description=description,
        category="Supplies",
        procurement_type="Open Bidding",
        published_at=datetime(2026, 9, 1, 9, 0, tzinfo=KAMPALA),
        deadline_at=NOW + timedelta(days=20),
        deadline_precision="datetime",
        status="open",
        sources=[SourceRef(name="eGP Uganda", url="https://example.com/bid", detected_at=NOW)],
    )


class ProcurementIntelligenceTests(unittest.TestCase):
    def test_extracts_bid_security_fee_and_submission_method(self):
        bid = make_bid(
            "Interested eligible bidders shall provide a Bid Security of UGX 5,000,000. "
            "A non-refundable bidding document fee of UGX 100,000 is payable. "
            "Bids must be delivered in a sealed envelope to the Procurement Unit."
        )
        intelligence = extract_intelligence(bid)
        self.assertIn("Bid Security", intelligence["bidSecurity"])
        self.assertIn("fee", intelligence["tenderFee"].lower())
        self.assertEqual(intelligence["submissionMethod"], "Physical / sealed submission")

    def test_detects_common_mandatory_requirements_without_inventing_others(self):
        bid = make_bid(
            "Bidders shall submit a tax clearance certificate, certificate of incorporation, "
            "audited financial statements and evidence of relevant experience."
        )
        intelligence = extract_intelligence(bid)
        self.assertIn("Tax clearance / tax compliance", intelligence["mandatoryRequirements"])
        self.assertIn("Certificate of incorporation / registration", intelligence["mandatoryRequirements"])
        self.assertIn("Audited financial statements", intelligence["mandatoryRequirements"])
        self.assertFalse(intelligence["bidSecurity"])

    def test_record_contains_intelligence_object(self):
        bid = make_bid("Quotations shall be submitted electronically by email. A site visit will be held on 10 September 2026.")
        record = record_from_bid(bid, "2026-09-03T11:30:00Z", NOW)
        self.assertIn("intelligence", record)
        self.assertEqual(record["intelligence"]["submissionMethod"], "Electronic submission by email")
        self.assertTrue(record["intelligence"]["keyDates"])


if __name__ == "__main__":
    unittest.main()
