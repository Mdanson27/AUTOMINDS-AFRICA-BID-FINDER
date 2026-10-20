from __future__ import annotations

import unittest

from src.egp_lifecycle import parse_beb_detail
from src.phase4_intelligence import _overlay_lifecycle
from src.sources.egp_uganda import EGPUgandaSource


LIST_HTML = """
<table>
  <thead><tr><th>Procuring Entity</th><th>Type</th><th>Subject of procurement</th><th>published</th><th>Deadline</th><th>Actions</th></tr></thead>
  <tbody><tr>
    <td><a href="/index/phase4_egp">POU/NCONS/2026-2027/00199 Parliament of Uganda</a></td>
    <td>Non Consultancy Services</td>
    <td>Routine maintenance of firefighting equipment</td>
    <td>2026-08-19</td><td>2026-11-16</td><td>View details</td>
  </tr></tbody>
</table>
"""


DEEP_DETAIL = """
<html><body>
<h1>Invitation to Bid</h1>
<table>
<tr><td>Procurement Reference Number</td><td>POU/NCONS/2026-2027/00199</td></tr>
<tr><td>Subject of Procurement</td><td>Framework contract for routine maintenance of firefighting equipment at Parliament</td></tr>
<tr><td>Procurement Method</td><td>Open Domestic Bidding</td></tr>
<tr><td>Submission Deadline</td><td>16 Nov 2026 at 11:00</td></tr>
<tr><td>Date and Time of bid Opening</td><td>16 Nov 2026 at 11:30</td></tr>
<tr><td>Bids received</td><td>2</td></tr>
<tr><td>Bid Security</td><td>UGX 5,000,000</td></tr>
<tr><td>Bidding Document Fee</td><td>UGX 100,000 non-refundable</td></tr>
<tr><td>Email</td><td>procurement@parliament.go.ug</td></tr>
<tr><td>Submission Address</td><td>Procurement and Disposal Unit, Parliament Avenue, Kampala</td></tr>
</table>
<h3>Mandatory Requirements</h3>
<ul><li>Valid tax clearance certificate</li><li>Registered power of attorney</li></ul>
<h3>Eligibility</h3><ul><li>Eligible firms registered in Uganda</li></ul>
<p>Bids shall be submitted electronically through the e-GP portal before the deadline.</p>
<a href="/documents/fire.pdf">Bidding Document</a>
<a href="/documents/addendum-1.pdf">Addendum No. 1</a>
<a href="/supplier/apply/199">Click here To Apply</a>
<table>
<tr><th>#</th><th>Name &amp; Address of The Bidder</th><th>Submission Date</th><th>Amount</th></tr>
<tr><td>1</td><td>ALPHA LTD (Plot 1 Kampala Road)</td><td>2026-11-15 09:00:00</td><td>UGX 120,000,000</td></tr>
<tr><td>2</td><td>BETA LTD (Plot 2 Jinja Road)</td><td>2026-11-15 10:30:00</td><td>UGX 135,000,000</td></tr>
</table>
<table>
<tr><th>No.</th><th>Name</th><th>Address</th><th>Position</th><th>Department/Company</th></tr>
<tr><td>1</td><td>Jane Doe</td><td>Kampala</td><td>Procurement Officer</td><td>Parliament</td></tr>
</table>
</body></html>
"""


BEB_HTML = """
<html><body>
<h1>BEST EVALUATED BIDDER NOTICE</h1>
<table>
<tr><td>Procurement Entity</td><td>Parliament of Uganda</td></tr>
<tr><td>Procurement Reference Number</td><td>POU/NCONS/2026-2027/00199</td></tr>
<tr><td>Subject of Procurement</td><td>Framework contract for routine maintenance of firefighting equipment at Parliament</td></tr>
<tr><td>Method of Procurement</td><td>Open Domestic Bidding Method</td></tr>
<tr><td>Name of Best Evaluated Bidder</td><td>ALPHA LTD</td></tr>
<tr><td>Total Contract Price</td><td>UGX :120,000,000.00 /= V.A.T Inclusive</td></tr>
<tr><td>Date for Display</td><td>20-11-2026</td></tr>
</table>
<table>
<tr><th>NO#</th><th>NAME OF BIDDER</th><th>PRICE</th><th>RANK</th><th>EVALUATION STAGE</th><th>REASONS OF FAILURE</th></tr>
<tr><td>1</td><td>BETA LTD</td><td>135,000,000</td><td>2</td><td>Financial Evaluation</td><td><ul><li>Higher evaluated price</li></ul></td></tr>
</table>
</body></html>
"""


class Phase4EGPIntelligenceTests(unittest.TestCase):
    def test_deep_detail_extracts_exact_procurement_intelligence(self):
        source = EGPUgandaSource()
        bid = list(source.parse(LIST_HTML))[0]
        enriched = source.parse_detail(DEEP_DETAIL, bid, "https://egpuganda.go.ug/index/phase4_egp")

        self.assertEqual(enriched.title, "Framework contract for routine maintenance of firefighting equipment at Parliament")
        self.assertEqual(enriched.procurement_method, "Open Domestic Bidding")
        self.assertEqual(enriched.deadline_at.hour, 11)
        self.assertEqual(enriched.deadline_precision, "datetime")
        self.assertEqual(enriched.opening_at.hour, 11)
        self.assertEqual(enriched.opening_at.minute, 30)
        self.assertEqual(enriched.bids_received, 2)
        self.assertEqual(enriched.bid_security, "UGX 5,000,000")
        self.assertEqual(enriched.tender_fee, "UGX 100,000 non-refundable")
        self.assertEqual(enriched.submission_method, "Electronic eGP portal submission")
        self.assertEqual(len(enriched.bidders), 2)
        self.assertEqual(enriched.bidders[0].name, "ALPHA LTD")
        self.assertEqual(enriched.bidders[0].address, "Plot 1 Kampala Road")
        self.assertEqual(enriched.bidders[0].currency, "UGX")
        self.assertEqual(len(enriched.opening_participants), 1)
        self.assertEqual(enriched.opening_participants[0].name, "Jane Doe")
        self.assertTrue(any(item.kind == "email" and item.value == "procurement@parliament.go.ug" for item in enriched.contacts))
        self.assertTrue(any("Submission Address" == item.label for item in enriched.contacts))
        self.assertTrue(any("Addendum" in item.title for item in enriched.amendments))
        self.assertTrue(any(item.stage == "advertised" for item in enriched.lifecycle_events))
        self.assertTrue(any(item.stage == "updated" for item in enriched.lifecycle_events))
        self.assertTrue(any(item.stage == "bid-opening" for item in enriched.lifecycle_events))

    def test_beb_parser_links_evaluation_to_reference(self):
        record = parse_beb_detail(BEB_HTML, "https://egpuganda.go.ug/best-evaluated-bidder-notice-report/123")
        self.assertIsNotNone(record)
        assert record is not None
        self.assertEqual(record["referenceNumber"], "POU/NCONS/2026-2027/00199")
        self.assertEqual(record["status"], "evaluation")
        self.assertEqual(record["bestEvaluatedBidder"], "ALPHA LTD")
        self.assertIn("120,000,000", record["contractAmount"])
        self.assertEqual(record["contractCurrency"], "UGX")
        self.assertTrue(any(item["stage"] == "evaluation" for item in record["lifecycleEvents"]))
        self.assertTrue(any(item["name"] == "BETA LTD" for item in record["bidders"]))

    def test_lifecycle_overlay_preserves_status_history_and_adds_source(self):
        lifecycle = parse_beb_detail(BEB_HTML, "https://egpuganda.go.ug/best-evaluated-bidder-notice-report/123")
        assert lifecycle is not None
        base = {
            "status": "closed",
            "isOpen": False,
            "statusHistory": [{"status": "closed", "at": "2026-11-16T08:00:00Z", "reason": "deadline-passed"}],
            "sources": [{"id": "egp-uganda", "name": "eGP Uganda", "url": "https://egpuganda.go.ug/index/phase4_egp", "detectedAt": "2026-08-19T00:00:00Z"}],
            "bidders": [],
            "lifecycleEvents": [],
            "sourceMetadata": {},
        }
        merged = _overlay_lifecycle(base, lifecycle)
        self.assertEqual(merged["status"], "evaluation")
        self.assertEqual(merged["statusHistory"][-1]["status"], "evaluation")
        self.assertEqual(merged["statusHistory"][-1]["reason"], "egp-lifecycle-evaluation")
        self.assertTrue(any(source["url"].endswith("/best-evaluated-bidder-notice-report/123") for source in merged["sources"]))


if __name__ == "__main__":
    unittest.main()
