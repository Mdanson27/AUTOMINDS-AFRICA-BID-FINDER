from __future__ import annotations

import unittest

from src.egp_plans import EGPProcurementPlansSource


INDEX_HTML = """
<html><body>
<table>
  <thead><tr><th>Plan Name</th><th>Financial Year</th><th>Actions</th></tr></thead>
  <tbody>
    <tr>
      <td>Parliament of Uganda</td>
      <td>2026-2027</td>
      <td>
        <a href="/index/54702_plan_2026-2027">VIEW</a>
        <a href="/plans/parliament.xlsx">Download Excel</a>
      </td>
    </tr>
    <tr>
      <td>Old Plan</td>
      <td>2025-2026</td>
      <td><a href="/index/old_plan">VIEW</a></td>
    </tr>
  </tbody>
</table>
</body></html>
"""

DETAIL_HTML = """
<html><body>
<h1>Parliament of Uganda Procurement Plan for 2026-2027</h1>
<a href="/plans/parliament.pdf">Download PDF</a>
<a href="/plans/parliament.xlsx">Download Excel</a>
<table>
  <thead><tr><th>No #</th><th>Group/Category</th><th>Estimated Amount in UGX:</th></tr></thead>
  <tbody>
    <tr><td>1</td><td>Computer programming and software development</td><td>1,446,567,125.00</td></tr>
    <tr><td>2</td><td>Computer Equipment and Accessories</td><td>4,199,932,875.00</td></tr>
    <tr><td>TOTAL</td><td>UGX:</td><td>5,646,500,000.00</td></tr>
  </tbody>
</table>
</body></html>
"""


class EGPProcurementPlanTests(unittest.TestCase):
    def test_index_keeps_only_requested_financial_year(self):
        source = EGPProcurementPlansSource()
        plans = source.parse_index(INDEX_HTML, financial_year="2026-2027")
        self.assertEqual(len(plans), 1)
        self.assertEqual(plans[0].organization, "Parliament of Uganda")
        self.assertEqual(plans[0].financial_year, "2026-2027")
        self.assertEqual(
            plans[0].source_url,
            "https://egpuganda.go.ug/index/54702_plan_2026-2027",
        )
        self.assertEqual(
            plans[0].excel_url,
            "https://egpuganda.go.ug/plans/parliament.xlsx",
        )

    def test_detail_parses_full_plan_categories_total_and_documents(self):
        source = EGPProcurementPlansSource()
        plan = source.parse_index(INDEX_HTML, financial_year="2026-2027")[0]
        enriched = source.parse_detail(DETAIL_HTML, plan)
        self.assertEqual(enriched.organization, "Parliament of Uganda")
        self.assertEqual(enriched.total_estimated_amount_ugx, "5,646,500,000.00")
        self.assertEqual(len(enriched.items), 2)
        self.assertEqual(
            enriched.items[0].category,
            "Computer programming and software development",
        )
        self.assertEqual(enriched.items[0].estimated_amount_ugx, "1,446,567,125.00")
        self.assertEqual(
            enriched.pdf_url,
            "https://egpuganda.go.ug/plans/parliament.pdf",
        )

    def test_current_financial_year_is_july_to_june(self):
        source = EGPProcurementPlansSource()
        from datetime import datetime
        from zoneinfo import ZoneInfo
        Kampala = ZoneInfo("Africa/Kampala")
        self.assertEqual(
            source.current_financial_year(datetime(2026, 9, 7, tzinfo=Kampala)),
            "2026-2027",
        )
        self.assertEqual(
            source.current_financial_year(datetime(2027, 3, 1, tzinfo=Kampala)),
            "2026-2027",
        )


if __name__ == "__main__":
    unittest.main()
