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
