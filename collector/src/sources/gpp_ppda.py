from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
import json
import re

import httpx

from .base import BidSource
from .common_web import KAMPALA, clean, parse_date
from ..models import NormalizedBid, SourceRef


class GPPPPDASource(BidSource):
    name = "GPP / PPDA"
    source_id = "gpp-ppda"
    url = "https://gpp.ppda.go.ug/public/bid-invitations"
    api_url = "https://gpp.ppda.go.ug/adminapi/public/api/tender/notices"
    financial_years = ("2026-2027", "2025-2026")

    def fetch(self) -> str:
        payload: dict[str, object] = {}
        headers = {
            "User-Agent": "AutoMindsBidFinder/1.0 (+public procurement indexing; Uganda)",
            "Accept": "application/json,text/plain,*/*",
        }
        with httpx.Client(timeout=45, follow_redirects=True, headers=headers) as client:
            for year in self.financial_years:
                response = client.get(self.api_url, params={"fy": year})
                response.raise_for_status()
                payload[year] = response.json()
        return json.dumps(payload)

    def parse(self, raw: str) -> Iterable[NormalizedBid]:
        payload = json.loads(raw)
        now = datetime.now(KAMPALA)
        discovered: dict[str, NormalizedBid] = {}

        for item in self._candidate_dicts(payload):
            title = self._pick(item, "subjectofprocurement", "procurementsubject", "subject", "title", "tendertitle", "description")
            organization = self._pick(item, "procuringentityname", "procuringentity", "entityname", "pdename", "organisation", "organization")
            if not title or not organization:
                continue

            reference = self._pick(item, "procurementreferencenumber", "referencenumber", "procurementreference", "reference", "procurementrefno")
            procurement_type = self._pick(item, "procurementtypename", "procurementtype", "type", "method") or "Government tender"
            category = self._pick(item, "sectorname", "sector", "category") or procurement_type
            published = parse_date(self._pick(item, "publicationdate", "datepublished", "publisheddate", "publishdate", "createdat"))
            deadline = parse_date(self._pick(item, "bidsubmissiondeadline", "submissiondeadline", "bidclosingdate", "closingdate", "deadline"))
            status = "open" if deadline is None or deadline >= now else "closed"
            notice_id = self._pick(item, "tendernoticeid", "noticeid", "tenderid", "id")
            source_url = f"https://gpp.ppda.go.ug/public/bid-invitations/tender-notice/{notice_id}" if notice_id else self.url

            bid = NormalizedBid(
                title=title,
                organization=organization,
                reference_number=reference,
                description=self._pick(item, "description", "details", "procurementdescription"),
                category=category,
                procurement_type=procurement_type,
                published_at=published,
                deadline_at=deadline,
                deadline_precision="datetime" if deadline else "unknown",
                status=status,
                sources=[SourceRef(name=self.name, url=source_url, detected_at=now)],
            )
            discovered[bid.canonical_key()] = bid

        return list(discovered.values())

    @classmethod
    def _candidate_dicts(cls, value):
        if isinstance(value, dict):
            normalized = {cls._norm(k) for k in value}
            has_title = bool(normalized & {"subjectofprocurement", "procurementsubject", "subject", "title", "tendertitle"})
            has_procurement_signal = bool(normalized & {"procuringentity", "procuringentityname", "procurementreferencenumber", "submissiondeadline", "bidsubmissiondeadline", "closingdate"})
            if has_title and has_procurement_signal:
                yield value
            for child in value.values():
                yield from cls._candidate_dicts(child)
        elif isinstance(value, list):
            for child in value:
                yield from cls._candidate_dicts(child)

    @classmethod
    def _pick(cls, item: dict, *names: str) -> str:
        wanted = set(names)
        for key, value in item.items():
            normalized = cls._norm(key)
            if normalized not in wanted:
                continue
            if isinstance(value, dict):
                for child_key in ("name", "title", "value", "label"):
                    if child_key in value and value[child_key] is not None:
                        return clean(str(value[child_key]))
                continue
            if value is not None:
                return clean(str(value))
        return ""

    @staticmethod
    def _norm(value: str) -> str:
        return re.sub(r"[^a-z0-9]", "", str(value).lower())
