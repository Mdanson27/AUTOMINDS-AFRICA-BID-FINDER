from __future__ import annotations

from datetime import datetime, timezone
import unittest

from src.postprocess_snapshot import apply_canonical_fields, process_records


class CanonicalBidIdentityTests(unittest.TestCase):
    def _record(self, **overrides):
        base = {
            "id": "old-id",
            "title": "Request For Quotations/Proposals",
            "organization": "Kampala Capital City Authority",
            "referenceNumber": "KCCA/NCONS/2026-2027/00255",
            "description": "",
            "category": "Non Consultancy Services",
            "procurementType": "Request For Quotations/Proposals",
            "publishedAt": "2026-10-10T00:00:00Z",
            "deadlineAt": "2026-10-20T23:59:59Z",
            "status": "open",
            "isOpen": True,
            "fingerprint": "old-fingerprint",
            "firstSeenAt": "2026-10-10T00:00:00Z",
            "lastSeenAt": "2026-10-20T08:00:00Z",
            "sources": [
                {
                    "id": "egp-uganda",
                    "name": "eGP Uganda",
                    "url": "https://egpuganda.go.ug/bid/notice/00255/opening/details",
                    "detectedAt": "2026-10-20T08:00:00Z",
                }
            ],
            "noticeType": "Procurement notice",
            "openingAt": "2026-10-20T08:14:00Z",
            "sourceMetadata": {
                "Subject of Procurement": "Procurement of Enterprise Systems Cybersecurity Audit Tools",
                "Procurement Method": "Request For Quotations/Proposals",
                "Date and Time of bid Opening": "20 Oct 2026 at 11:14",
                "Bids received": "2",
            },
        }
        base.update(overrides)
        return base

    def test_subject_of_procurement_overrides_vague_method_title(self):
        result = apply_canonical_fields(self._record())
        self.assertEqual(result["title"], "Procurement of Enterprise Systems Cybersecurity Audit Tools")
        self.assertEqual(result["procurementMethod"], "Request For Quotations/Proposals")
        self.assertEqual(result["noticeType"], "Procurement notice")
        self.assertEqual(result["sourceStage"], "Bid opening")
        self.assertEqual(result["canonicalSource"], "eGP Uganda")
        self.assertEqual(result["titleSpecificity"], "specific")
        self.assertTrue(result["displayEligible"])

    def test_method_never_overwrites_real_subject(self):
        result = apply_canonical_fields(
            self._record(
                title="Procurement of Enterprise Systems Cybersecurity Audit Tools",
                sourceMetadata={"Procurement Method": "Request For Quotations/Proposals"},
            )
        )
        self.assertEqual(result["title"], "Procurement of Enterprise Systems Cybersecurity Audit Tools")
        self.assertEqual(result["procurementMethod"], "Request For Quotations/Proposals")

    def test_identity_uses_reference_and_organization_not_reference_alone(self):
        first = apply_canonical_fields(self._record())
        second = apply_canonical_fields(self._record(organization="Another Procuring Entity"))
        self.assertNotEqual(first["canonicalIdentity"], second["canonicalIdentity"])
        self.assertNotEqual(first["id"], second["id"])
        self.assertIn("kcca/ncons/2026-2027/00255", first["canonicalIdentity"])
        self.assertIn("kampala capital city authority", first["canonicalIdentity"])

    def test_identity_without_reference_uses_org_title_and_source(self):
        first = apply_canonical_fields(self._record(referenceNumber=""))
        second = apply_canonical_fields(
            self._record(
                referenceNumber="",
                title="Different procurement",
                sourceMetadata={
                    "Subject of Procurement": "Different procurement",
                    "Procurement Method": "Request For Quotations/Proposals",
                },
            )
        )
        self.assertNotEqual(first["canonicalIdentity"], second["canonicalIdentity"])
        self.assertTrue(first["canonicalIdentity"].startswith("org-title-source:"))

    def test_process_records_preserves_field_separation(self):
        now = datetime(2026, 10, 20, 12, 0, tzinfo=timezone.utc)
        result = process_records([self._record()], now)
        self.assertEqual(len(result), 1)
        record = result[0]
        self.assertEqual(record["title"], "Procurement of Enterprise Systems Cybersecurity Audit Tools")
        self.assertEqual(record["organization"], "Kampala Capital City Authority")
        self.assertEqual(record["referenceNumber"], "KCCA/NCONS/2026-2027/00255")
        self.assertEqual(record["procurementMethod"], "Request For Quotations/Proposals")
        self.assertEqual(record["noticeType"], "Procurement notice")
        self.assertEqual(record["sourceStage"], "Bid opening")
        self.assertEqual(record["deadlineAt"], "2026-10-20T23:59:59Z")
        self.assertEqual(record["canonicalSource"], "eGP Uganda")

    def test_global_rule_strips_method_prefix_when_title_contains_real_subject(self):
        result = apply_canonical_fields(
            self._record(
                title="Request for Proposals: Provision of Managed Network Security Services",
                sourceMetadata={"Procurement Method": "Request for Proposals"},
                sources=[{
                    "id": "world-bank-uganda",
                    "name": "World Bank Uganda",
                    "url": "https://example.org/opportunity/1",
                    "detectedAt": "2026-10-20T08:00:00Z",
                }],
            )
        )
        self.assertEqual(result["title"], "Provision of Managed Network Security Services")
        self.assertTrue(result["displayEligible"])

    def test_global_rule_recovers_specific_subject_from_description(self):
        result = apply_canonical_fields(
            self._record(
                title="Open Domestic",
                description="The entity invites eligible bidders for the supply of laptops, desktop computers and related ICT accessories for regional offices.",
                sourceMetadata={"Procurement Method": "Open Domestic Bidding"},
                sources=[{
                    "id": "new-vision",
                    "name": "New Vision",
                    "url": "https://www.newvision.co.ug/opportunities/notices-123",
                    "detectedAt": "2026-10-20T08:00:00Z",
                }],
            )
        )
        self.assertEqual(result["title"], "supply of laptops, desktop computers and related ICT accessories for regional offices")
        self.assertEqual(result["titleSource"], "description")
        self.assertTrue(result["displayEligible"])

    def test_global_rule_uses_scope_metadata_for_any_source(self):
        result = apply_canonical_fields(
            self._record(
                title="Micro Procurement",
                sourceMetadata={
                    "Scope of Work": "Maintenance of air conditioning systems at the headquarters and regional offices",
                    "Procurement Method": "Micro Procurement",
                },
                sources=[{
                    "id": "kcca",
                    "name": "KCCA",
                    "url": "https://example.org/tender/2",
                    "detectedAt": "2026-10-20T08:00:00Z",
                }],
            )
        )
        self.assertEqual(result["title"], "Maintenance of air conditioning systems at the headquarters and regional offices")
        self.assertTrue(result["displayEligible"])

    def test_unresolved_generic_title_is_retained_but_not_display_eligible(self):
        result = apply_canonical_fields(
            self._record(
                title="Request for Proposals",
                description="",
                sourceMetadata={"Procurement Method": "Request for Proposals"},
                sources=[{
                    "id": "daily-monitor",
                    "name": "Daily Monitor",
                    "url": "https://www.monitor.co.ug/uganda/advertise/tenders/example",
                    "detectedAt": "2026-10-20T08:00:00Z",
                }],
            )
        )
        self.assertEqual(result["titleSpecificity"], "unresolved")
        self.assertFalse(result["displayEligible"])
        self.assertTrue(result["canonicalIdentity"].startswith("ref-org:"))


if __name__ == "__main__":
    unittest.main()
