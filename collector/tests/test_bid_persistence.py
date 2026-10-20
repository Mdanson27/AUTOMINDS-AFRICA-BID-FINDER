from __future__ import annotations

from datetime import datetime, timezone
import unittest

from src.bid_persistence import merge_persistent_records


NOW = datetime(2026, 10, 20, 10, 0, tzinfo=timezone.utc)
RUN_AT = "2026-10-20T10:00:00Z"


class BidPersistenceTests(unittest.TestCase):
    def _bid(self, **overrides):
        base = {
            "id": "bid-1",
            "canonicalIdentity": "ref-org:kcca/supls/2026-2027/00101|kampala capital city authority",
            "fingerprint": "ref-org:kcca/supls/2026-2027/00101|kampala capital city authority",
            "title": "Supply of office dispensable items",
            "organization": "Kampala Capital City Authority",
            "referenceNumber": "KCCA/SUPLS/2026-2027/00101",
            "deadlineAt": "2026-11-20T20:59:59Z",
            "status": "open",
            "isOpen": True,
            "firstDetectedAt": "2026-10-01T08:00:00Z",
            "firstSeenAt": "2026-10-01T08:00:00Z",
            "lastSeenAt": "2026-10-19T08:00:00Z",
            "lastVerifiedAt": "2026-10-19T08:00:00Z",
            "sources": [
                {
                    "id": "egp-uganda",
                    "name": "eGP Uganda",
                    "url": "https://egpuganda.go.ug/index/101",
                }
            ],
            "statusHistory": [
                {"status": "open", "at": "2026-10-01T08:00:00Z", "reason": "discovered-and-verified"}
            ],
        }
        base.update(overrides)
        return base

    def test_failed_scan_never_deletes_active_bid(self):
        previous = [self._bid()]
        metas = [{"id": "egp-uganda", "name": "eGP Uganda", "health": "warning"}]
        result = merge_persistent_records(previous, [], metas, now=NOW, generated_at=RUN_AT)
        self.assertEqual(len(result), 1)
        retained = result[0]
        self.assertEqual(retained["status"], "open")
        self.assertTrue(retained["isOpen"])
        self.assertEqual(retained["verificationStatus"], "source-unavailable")
        self.assertEqual(retained["lastSeenAt"], "2026-10-19T08:00:00Z")
        self.assertEqual(retained["lastVerifiedAt"], "2026-10-19T08:00:00Z")

    def test_fewer_records_from_healthy_source_do_not_remove_known_open_bid(self):
        first = self._bid()
        second = self._bid(
            id="bid-2",
            canonicalIdentity="ref-org:kcca/supls/2026-2027/00102|kampala capital city authority",
            fingerprint="ref-org:kcca/supls/2026-2027/00102|kampala capital city authority",
            referenceNumber="KCCA/SUPLS/2026-2027/00102",
            title="Supply of network equipment",
        )
        current_second = dict(second)
        result = merge_persistent_records(
            [first, second],
            [current_second],
            [{"id": "egp-uganda", "name": "eGP Uganda", "health": "healthy"}],
            now=NOW,
            generated_at=RUN_AT,
        )
        self.assertEqual(len(result), 2)
        by_ref = {item["referenceNumber"]: item for item in result}
        self.assertIn("KCCA/SUPLS/2026-2027/00101", by_ref)
        self.assertEqual(
            by_ref["KCCA/SUPLS/2026-2027/00101"]["verificationStatus"],
            "not-seen-current-scan",
        )

    def test_90_day_rule_does_not_remove_already_discovered_bid(self):
        previous = [self._bid(deadlineAt="2027-03-15T20:59:59Z")]
        result = merge_persistent_records(
            previous,
            [],
            [{"id": "egp-uganda", "name": "eGP Uganda", "health": "healthy"}],
            now=NOW,
            generated_at=RUN_AT,
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["deadlineAt"], "2027-03-15T20:59:59Z")
        self.assertEqual(result[0]["status"], "open")

    def test_deadline_passed_moves_record_to_closed_history(self):
        previous = [self._bid(deadlineAt="2026-10-19T20:59:59Z")]
        result = merge_persistent_records(
            previous,
            [],
            [{"id": "egp-uganda", "name": "eGP Uganda", "health": "warning"}],
            now=NOW,
            generated_at=RUN_AT,
        )
        closed = result[0]
        self.assertEqual(closed["status"], "closed")
        self.assertFalse(closed["isOpen"])
        self.assertEqual(closed["retentionStatus"], "expired")
        self.assertEqual(closed["statusHistory"][-1]["status"], "closed")
        self.assertEqual(closed["statusHistory"][-1]["reason"], "deadline-passed")

    def test_seen_bid_preserves_first_detection_and_updates_verification_times(self):
        previous = [self._bid()]
        current = self._bid(
            firstDetectedAt="2026-10-20T10:00:00Z",
            firstSeenAt="2026-10-20T10:00:00Z",
            lastSeenAt="2026-10-20T10:00:00Z",
            lastVerifiedAt="2026-10-20T10:00:00Z",
        )
        result = merge_persistent_records(
            previous,
            [current],
            [{"id": "egp-uganda", "name": "eGP Uganda", "health": "healthy"}],
            now=NOW,
            generated_at=RUN_AT,
        )
        seen = result[0]
        self.assertEqual(seen["firstDetectedAt"], "2026-10-01T08:00:00Z")
        self.assertEqual(seen["firstSeenAt"], "2026-10-01T08:00:00Z")
        self.assertEqual(seen["lastSeenAt"], RUN_AT)
        self.assertEqual(seen["lastVerifiedAt"], RUN_AT)
        self.assertEqual(seen["verificationStatus"], "verified")

    def test_deadline_extension_is_recorded_without_creating_new_identity(self):
        previous = [self._bid(deadlineAt="2026-11-20T20:59:59Z")]
        current = self._bid(deadlineAt="2026-12-05T20:59:59Z")
        result = merge_persistent_records(
            previous,
            [current],
            [{"id": "egp-uganda", "name": "eGP Uganda", "health": "healthy"}],
            now=NOW,
            generated_at=RUN_AT,
        )
        self.assertEqual(len(result), 1)
        self.assertTrue(result[0]["deadlineChanged"])
        self.assertEqual(result[0]["canonicalIdentity"], previous[0]["canonicalIdentity"])


if __name__ == "__main__":
    unittest.main()
