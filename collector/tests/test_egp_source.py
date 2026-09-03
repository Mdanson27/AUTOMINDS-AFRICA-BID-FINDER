from __future__ import annotations

from datetime import datetime
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
</body></html>
"""


class EGPUgandaSourceTests(unittest.TestCase):
    def test_parses_standard_bid_notice_table(self):
        bids = list(EGPUgandaSource().parse(HTML))
        self.assertEqual(len(bids), 2)
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

    def test_reference_drives_cross_source_canonical_key(self):
        bid = list(EGPUgandaSource().parse(HTML))[0]
        self.assertEqual(bid.canonical_key(), "ref:pou/ncons/2026-2027/00199")

    def test_date_only_deadline_is_end_of_day(self):
        bid = list(EGPUgandaSource().parse(HTML))[0]
        self.assertEqual(bid.deadline_at.hour, 23)
        self.assertEqual(bid.deadline_at.minute, 59)
        self.assertEqual(bid.deadline_at.second, 59)

    def test_ignores_unrelated_tables(self):
        raw = "<table><tr><th>Name</th></tr><tr><td>Nothing</td></tr></table>"
        self.assertEqual(list(EGPUgandaSource().parse(raw)), [])


if __name__ == "__main__":
    unittest.main()
