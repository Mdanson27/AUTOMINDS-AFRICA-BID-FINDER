from __future__ import annotations

from datetime import datetime, timedelta
import unittest

from src.export_30_source_snapshot import NETWORK_SOURCES, validate_network
from src.sources.common_web import KAMPALA
from src.sources.public_portals import PortalConfig, PublicProcurementPortalSource


class SourceNetworkTests(unittest.TestCase):
    def test_network_contains_30_unique_sources(self):
        validate_network()
        ids = [source.source_id for source in NETWORK_SOURCES]
        self.assertEqual(30, len(ids))
        self.assertEqual(30, len(set(ids)))

    def test_generic_portal_parser_requires_live_deadline(self):
        source = PublicProcurementPortalSource(
            PortalConfig(
                "fixture",
                "Fixture Source",
                "https://example.org/tenders",
                "Fixture Uganda",
                "government",
            )
        )
        now = datetime.now(KAMPALA)
        live_date = (now + timedelta(days=30)).strftime("%d %B %Y")
        expired_date = (now - timedelta(days=30)).strftime("%d %B %Y")
        html = f"""
        <main>
          <article>
            <h3>Invitation to Bid for Supply of Network Equipment</h3>
            <p>Procurement Reference No: TEST/SUPLS/2026/001</p>
            <p>Closing date: {live_date}</p>
            <a href="/tenders/1">Read more</a>
          </article>
          <article>
            <h3>Invitation to Bid for Expired Office Supplies</h3>
            <p>Closing date: {expired_date}</p>
          </article>
        </main>
        """
        bids = list(source.parse(html))
        self.assertEqual(1, len(bids))
        self.assertEqual("TEST/SUPLS/2026/001", bids[0].reference_number)
        self.assertEqual(23, bids[0].deadline_at.hour)
        self.assertEqual("open", bids[0].status)

    def test_country_filter_blocks_other_countries(self):
        source = PublicProcurementPortalSource(
            PortalConfig(
                "global-fixture",
                "Global Fixture",
                "https://example.org/tenders",
                "Global Organization",
                "development",
                ("uganda", "kampala"),
            )
        )
        live_date = (datetime.now(KAMPALA) + timedelta(days=30)).strftime("%d %B %Y")
        html = f"""
        <article>
          <h3>Invitation to Tender for Vehicle Supply</h3>
          <p>Country: Kenya</p>
          <p>Deadline: {live_date}</p>
        </article>
        """
        self.assertEqual([], list(source.parse(html)))


if __name__ == "__main__":
    unittest.main()
