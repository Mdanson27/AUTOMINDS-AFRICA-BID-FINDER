from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
import json
import re

import httpx

from .base import BidSource
from .common_web import KAMPALA, clean, parse_date
from ..models import NormalizedBid, SourceRef


class WorldBankUgandaSource(BidSource):
    name = "World Bank Uganda"
    source_id = "world-bank-uganda"
    url = "https://projects.worldbank.org/en/projects-operations/opportunities"
    api_url = "https://search.worldbank.org/api/v2/procnotices"

    def fetch(self) -> str:
        response = httpx.get(
            self.api_url,
            timeout=45,
            follow_redirects=True,
            params={
                "format": "json",
                "rows": 200,
                "os": 0,
                "project_ctry_name": "Uganda",
                "srt": "submission_deadline_date",
                "order": "desc",
                "apilang": "en",
                "srce": "both",
            },
            headers={
                "User-Agent": "AutoMindsBidFinder/1.0 (+public procurement indexing; Uganda)",
                "Accept": "application/json",
            },
        )
        response.raise_for_status()
        return response.text

    def parse(self, raw: str) -> Iterable[NormalizedBid]:
        payload = json.loads(raw)
        now = datetime.now(KAMPALA)
        discovered: dict[str, NormalizedBid] = {}

        for item in self._candidate_dicts(payload):
            country = self._pick(item, "project_ctry_name", "country_name", "country")
            if country and "uganda" not in country.lower():
                continue

            notice_text = self._pick(item, "notice_text")
            project_name = self._pick(item, "project_name")
            project_id = self._pick(item, "project_id")
            reference = self._pick(item, "reference_no", "reference", "notice_reference", "id")
            notice_type = self._pick(item, "notice_type", "notice_type_exact") or "Procurement notice"
            procurement_type = self._pick(item, "procurement_group_desc", "procurement_type", "procurement_method_name") or notice_type
            explicit_title = self._pick(item, "notice_title", "title", "short_description")

            if explicit_title:
                title = explicit_title
            elif project_name:
                suffix = procurement_type if procurement_type.lower() not in project_name.lower() else ""
                title = clean(f"{project_name}{' — ' + suffix if suffix else ''}")
            else:
                title = clean(notice_text)[:180]

            if not title:
                continue

            published = parse_date(self._pick(item, "publication_date", "published_date", "date_published"))
            deadline = parse_date(self._pick(item, "submission_deadline_date", "submission_date", "deadline_date", "deadline"))
            status = "open" if deadline is None or deadline >= now else "closed"
            notice_id = self._pick(item, "id", "notice_id")
            source_url = (
                f"https://projects.worldbank.org/en/projects-operations/procurement-detail/{notice_id}"
                if notice_id else self.url
            )
            agency = self._pick(
                item,
                "implementing_agency",
                "implementing_agency_name",
                "borrower",
                "agency_name",
                "organization",
            )
            description = clean(" | ".join(part for part in (project_name, project_id, notice_text) if part))
            bid = NormalizedBid(
                title=title[:240],
                organization=agency or project_name or "World Bank / Uganda project",
                reference_number=reference,
                description=description[:1600],
                category=self._pick(item, "sector", "sector_name", "procurement_group_desc") or procurement_type,
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
            keys = {cls._norm(key) for key in value}
            if keys & {"noticetext", "noticetitle", "submissiondeadlinedate"}:
                yield value
            for child in value.values():
                yield from cls._candidate_dicts(child)
        elif isinstance(value, list):
            for child in value:
                yield from cls._candidate_dicts(child)

    @classmethod
    def _pick(cls, item: dict, *names: str) -> str:
        wanted = {cls._norm(name) for name in names}
        for key, value in item.items():
            if cls._norm(key) in wanted and value is not None:
                if isinstance(value, (str, int, float)):
                    return clean(str(value))
        return ""

    @staticmethod
    def _norm(value: str) -> str:
        return re.sub(r"[^a-z0-9]", "", str(value).lower())
