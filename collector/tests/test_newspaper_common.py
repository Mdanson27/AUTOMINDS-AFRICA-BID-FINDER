from __future__ import annotations

import unittest

from src.export_live_snapshot import newspaper_meta
from src.sources.daily_monitor import DailyMonitorSource
from src.sources.newspaper_common import CaptureReport, domain_matches, looks_incomplete_html, parse_notice_page


NOTICE_HTML = """
<html><body>
<article>
  <h1>INVITATION TO BID FOR SUPPLY OF ICT EQUIPMENT</h1>
  <time datetime="2026-10-01T08:00:00+03:00"></time>
  <p>ABC Uganda invites eligible bidders. Ref: ABC/ICT/2026/17.</p>
  <p>Submission deadline is 28 October 2026 at 11:00 AM.</p>
  <a href="/docs/abc-ict.pdf">Download bid document</a>
</article>
</body></html>
"""


class NewspaperCaptureTests(unittest.TestCase):
    def test_domain_matching_is_strict(self):
        self.assertTrue(domain_matches("https://www.newvision.co.ug/opportunities/tenders-123", "newvision.co.ug"))
        self.assertTrue(domain_matches("https://monitor.co.ug/uganda/jobs/tenders/example", "monitor.co.ug"))
        self.assertFalse(domain_matches("https://example.com/copy/newvision", "newvision.co.ug"))
        self.assertFalse(domain_matches("https://newvision.co.ug.example.com/fake", "newvision.co.ug"))

    def test_dynamic_empty_shell_is_incomplete(self):
        self.assertTrue(looks_incomplete_html("<html><body>Loading data...</body></html>"))
        self.assertTrue(looks_incomplete_html("<html><body>No articles available.</body></html>"))
        self.assertFalse(looks_incomplete_html("<html><body><article>Procurement notice</article></body></html>"))

    def test_notice_extraction_preserves_newspaper_source(self):
        bid = parse_notice_page(
            NOTICE_HTML,
            "https://www.monitor.co.ug/uganda/jobs/tenders/abc-ict-123",
            "Daily Monitor",
            "monitor.co.ug",
        )
        self.assertIsNotNone(bid)
        assert bid is not None
        self.assertEqual(bid.sources[0].name, "Daily Monitor")
        self.assertTrue(str(bid.sources[0].url).startswith("https://www.monitor.co.ug/"))
        self.assertEqual(bid.reference_number, "ABC/ICT/2026/17")
        self.assertIsNotNone(bid.deadline_at)
        self.assertEqual(bid.source_metadata.get("canonicalPublisher"), "Daily Monitor")
        self.assertIn(bid.source_metadata.get("verification"), {"VERIFIED", "MANUAL_REVIEW"})
        self.assertEqual(len(bid.documents), 1)

    def test_incomplete_capture_never_reports_false_zero(self):
        source = DailyMonitorSource()
        source.capture_report = CaptureReport(
            source_status="BLOCKED",
            capture_status="INCOMPLETE",
            http_status=403,
            direct_status="blocked_403",
            discovery_status="no_results",
        )
        meta = newspaper_meta(source, "2026-10-20T08:00:00Z", [], [])
        self.assertIsNone(meta["recordsFound"])
        self.assertEqual(meta["collectorStatus"], "BLOCKED")
        self.assertEqual(meta["captureStatus"], "INCOMPLETE")

    def test_successful_empty_capture_can_report_zero(self):
        source = DailyMonitorSource()
        source.capture_report = CaptureReport(
            source_status="HEALTHY",
            capture_status="SUCCESS",
            direct_status="success",
            render_status="success",
            discovery_status="active",
        )
        meta = newspaper_meta(source, "2026-10-20T08:00:00Z", [], [])
        self.assertEqual(meta["recordsFound"], 0)


if __name__ == "__main__":
    unittest.main()
