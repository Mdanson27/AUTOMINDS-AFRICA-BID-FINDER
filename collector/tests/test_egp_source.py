from __future__ import annotations

import unittest
from zoneinfo import ZoneInfo

from src.sources.egp_uganda import EGPUgandaSource


HTML = """
<html><body>
<table>
  <thead><tr>
    <th>Procuring Entity</th><th>Type</th><th>Subject of procurement</th><th>published</th><th>Deadline</th><th>Actions</th>
  </tr></thead>
  <tbody>
    <tr>
      <td><a href="/index/392535474_egp">POU/NCONS/2026-2027/00199 Parliament of Uganda</a></td>
      <td>Non Consultancy Services</td>
      <td>Framework contract for routine maintenance of firefighting equipment</td>
      <td>2026-08-19</td>
      <td>2026-09-16</td>
      <td>View details</td>
    </tr>
    <tr>
      <td><a href="/index/other_egp">KCCA/SUPLS/2026-2027/00101 Kampala Capital City Authority</a></td>
      <td>Supplies</td>
      <td>PROCUREMENT FOR SUPPLY OF OFFICE DISPENSABLE ITEMS</td>
      <td>2026-08-26</td>
      <td>2026-09-16</td>
      <td>View details</td>
    </tr>
  </tbody>
</table>
<table>
  <thead><tr>
    <th>Procurement &amp; Disposal Entity</th><th>Procurement Method</th><th>Bid Details</th><th>Deadline</th><th>Opening Date/Time</th><th>Actions</th>
  </tr></thead>
  <tbody>
    <tr>
      <td><a href="/index/micro_egp">MoFA/NCONS/2026-2027/00012 Ministry of Foreign Affairs</a></td>
      <td>Micro Procurement</td>
      <td><span title="PROCUREMENT OF MOTOR VEHICLE REPAIR SERVICES">PROCUREMENT OF MOTOR...</span></td>
      <td>2026-09-05</td>
      <td>2026-09-05</td>
      <td>View Details</td>
    </tr>
  </tbody>
</table>
</body></html>
"""



DETAIL_HTML = """
<html><body>
<h1>Request for Quotation Notice</h1>
<table>
  <tr><th>No #</th><th>Procurement Ref Number</th><th>Subject of Procurement</th></tr>
  <tr><td>1</td><td>POU/NCONS/2026-2027/00199</td><td>Framework contract for routine maintenance of firefighting equipment at Parliament of Uganda</td></tr>
</table>
<p>Parliament of Uganda invites eligible suppliers to submit a bid for the above opportunity.</p>
<a href="/supplier/apply/199">Click here To Apply</a>
<a href="/documents/firefighting-tender.pdf">Download PDF</a>
</body></html>
"""

OPENING_DETAIL_HTML = """
<html><body>
<h1>Particulars of Procurement</h1>
<table>
  <tr><td>Subject of Procurement</td><td>REPAIRS FOR UG 2600133</td></tr>
  <tr><td>Procurement Method</td><td>Micro Procurement</td></tr>
  <tr><td>Date and Time of bid Opening</td><td>31 Aug 2026 at 15:19</td></tr>
  <tr><td>Bids received</td><td>1</td></tr>
</table>
<table>
  <tr><th>#</th><th>Name &amp; Address of The Bidder</th><th>Submission Date</th><th>Amount</th></tr>
  <tr><td>1</td><td>CFAO MOBILITY UGANDA LIMITED</td><td>2026-08-28 15:47:28</td><td>5,702,639.88</td></tr>
</table>
</body></html>
"""


class EGPUgandaSourceTests(unittest.TestCase):
    def test_parses_standard_and_quotation_tables(self):
        bids = list(EGPUgandaSource().parse(HTML))
        self.assertEqual(len(bids), 3)
        first = bids[0]
        self.assertEqual(first.reference_number, "POU/NCONS/2026-2027/00199")
        self.assertEqual(first.organization, "Parliament of Uganda")
        self.assertEqual(first.procurement_type, "Non Consultancy Services")
        self.assertEqual(
            str(first.sources[0].url),
            "https://egpuganda.go.ug/index/392535474_egp",
        )
        self.assertEqual(first.deadline_precision, "date")
        self.assertEqual(first.deadline_at.tzinfo, ZoneInfo("Africa/Kampala"))

        quotation = bids[2]
        self.assertEqual(quotation.reference_number, "MoFA/NCONS/2026-2027/00012")
        self.assertEqual(quotation.organization, "Ministry of Foreign Affairs")
        self.assertEqual(quotation.procurement_type, "Micro Procurement")
        self.assertEqual(quotation.title, "PROCUREMENT OF MOTOR VEHICLE REPAIR SERVICES")
        self.assertIsNone(quotation.published_at)
        self.assertEqual(str(quotation.sources[0].url), "https://egpuganda.go.ug/index/micro_egp")

    def test_detail_enrichment_recovers_full_title_apply_link_and_documents(self):
        source = EGPUgandaSource()
        bid = list(source.parse(HTML))[0]
        enriched = source.parse_detail(
            DETAIL_HTML,
            bid,
            "https://egpuganda.go.ug/index/392535474_egp",
        )
        self.assertEqual(
            enriched.title,
            "Framework contract for routine maintenance of firefighting equipment at Parliament of Uganda",
        )
        self.assertEqual(enriched.notice_type, "Request for Quotation Notice")
        self.assertIn("invites eligible suppliers", enriched.description)
        self.assertEqual(
            str(enriched.application_url),
            "https://egpuganda.go.ug/supplier/apply/199",
        )
        self.assertEqual(len(enriched.documents), 1)
        self.assertEqual(enriched.documents[0].kind, "PDF")

    def test_opening_detail_captures_method_time_bidder_and_amount(self):
        source = EGPUgandaSource()
        bid = list(source.parse(HTML))[2]
        enriched = source.parse_detail(
            OPENING_DETAIL_HTML,
            bid,
            "https://egpuganda.go.ug/bid/notice/147427968/opening/details",
        )
        self.assertEqual(enriched.title, "REPAIRS FOR UG 2600133")
        self.assertEqual(enriched.procurement_type, "Micro Procurement")
        self.assertEqual(enriched.opening_at.day, 31)
        self.assertEqual(enriched.opening_at.hour, 15)
        self.assertEqual(enriched.source_metadata["Bids received"], "1")
        self.assertIn(
            "CFAO MOBILITY UGANDA LIMITED",
            enriched.source_metadata["Bid opening 1 · Name & Address of The Bidder"],
        )
        self.assertEqual(
            enriched.source_metadata["Bid opening 1 · Amount"],
            "5,702,639.88",
        )

    def test_reference_drives_cross_source_canonical_key(self):
        bid = list(EGPUgandaSource().parse(HTML))[0]
        self.assertEqual(bid.canonical_key(), "ref:pou/ncons/2026-2027/00199")

    def test_date_only_deadline_is_end_of_day(self):
        bid = list(EGPUgandaSource().parse(HTML))[0]
        self.assertEqual(bid.deadline_at.hour, 23)
        self.assertEqual(bid.deadline_at.minute, 59)
        self.assertEqual(bid.deadline_at.second, 59)

    def test_deduplicates_same_reference_before_database(self):
        raw = HTML.replace("</body></html>", "") + """
        <table><thead><tr><th>Procuring Entity</th><th>Type</th><th>Subject of procurement</th><th>published</th><th>Deadline</th></tr></thead>
        <tbody><tr><td>POU/NCONS/2026-2027/00199 Parliament of Uganda</td><td>Non Consultancy Services</td><td>Updated title</td><td>2026-08-19</td><td>2026-09-17</td></tr></tbody></table>
        </body></html>"""
        bids = list(EGPUgandaSource().parse(raw))
        matching = [bid for bid in bids if bid.reference_number == "POU/NCONS/2026-2027/00199"]
        self.assertEqual(len(matching), 1)
        self.assertEqual(matching[0].deadline_at.day, 17)

    def test_ignores_unrelated_tables(self):
        raw = "<table><tr><th>Name</th></tr><tr><td>Nothing</td></tr></table>"
        self.assertEqual(list(EGPUgandaSource().parse(raw)), [])


if __name__ == "__main__":
    unittest.main()
