import unittest

from collector.src.neon_sync import _bid_row, _grant_row, _plan_row, _source_row


class NeonSyncMappingTests(unittest.TestCase):
    def test_bid_mapping_preserves_deadline_and_raw_record(self):
        bid = {
            "id": "bid-1",
            "title": "Supply of ICT equipment",
            "organization": "Example Agency",
            "referenceNumber": "EA/SUPLS/2026/01",
            "deadlineAt": "2026-11-20T14:00:00+03:00",
            "publishedAt": "2026-10-30T09:00:00+03:00",
            "status": "open",
            "isOpen": True,
            "displayEligible": True,
            "sources": [{"id": "egp-uganda", "name": "eGP Uganda", "url": "https://example.test/bid/1"}],
        }
        row = _bid_row(bid)
        self.assertEqual(row["id"], "bid-1")
        self.assertEqual(row["reference_number"], "EA/SUPLS/2026/01")
        self.assertEqual(row["deadline_at"], bid["deadlineAt"])
        self.assertEqual(row["raw_record"], bid)

    def test_plan_mapping_preserves_frontend_shape_in_raw_record(self):
        plan = {
            "id": "plan-1",
            "name": "FY 2026/27 Procurement Plan",
            "organization": "Example Agency",
            "financialYear": "2026/27",
            "totalEstimatedAmountUGX": "100000000",
            "sourceUrl": "https://example.test/plans/1",
            "items": [{"number": 1, "category": "Supplies", "estimatedAmountUGX": "100000000"}],
        }
        row = _plan_row(plan)
        self.assertEqual(row["financial_year"], "2026/27")
        self.assertEqual(row["items"], plan["items"])
        self.assertEqual(row["raw_record"], plan)

    def test_grant_without_deadline_is_not_written(self):
        self.assertIsNone(_grant_row({"id": "grant-1", "title": "No verified deadline"}))

    def test_source_defaults_are_safe(self):
        row = _source_row({"id": "test-source", "name": "Test Source"})
        self.assertEqual(row["id"], "test-source")
        self.assertTrue(row["enabled"])
        self.assertEqual(row["health"], "planned")


if __name__ == "__main__":
    unittest.main()
