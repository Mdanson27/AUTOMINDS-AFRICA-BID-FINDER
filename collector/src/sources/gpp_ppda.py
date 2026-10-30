from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
import json
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup
import httpx

from .base import BidSource
from .common_web import KAMPALA, clean, extract_deadline, extract_reference, parse_date
from ..models import NormalizedBid, SourceRef


class GPPPPDASource(BidSource):
    name = "GPP / PPDA"
    source_id = "gpp-ppda"
    url = "https://gpp.ppda.go.ug/public/bid-invitations"
    api_url = "https://gpp.ppda.go.ug/adminapi/public/api/tender/notices"
    financial_years = ("2026-2027", "2025-2026")

    def fetch(self) -> str:
        """Use the historical JSON endpoint first, then the real public UI.

        GPP is an Angular application and its old public JSON endpoint sometimes
        returns HTML instead of JSON. The browser fallback reads the canonical
        public tender page itself, so GPP remains a first-class source rather
        than silently disappearing whenever that undocumented endpoint changes.
        """
        payload: dict[str, object] = {}
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; AutoMindsBidFinder/2.0; +https://automindsafrica.com)",
            "Accept": "application/json,text/plain,*/*",
        }
        try:
            with httpx.Client(timeout=25, follow_redirects=True, headers=headers) as client:
                for year in self.financial_years:
                    response = client.get(self.api_url, params={"fy": year})
                    response.raise_for_status()
                    content_type = response.headers.get("content-type", "").lower()
                    if "json" not in content_type and not response.text.lstrip().startswith(("{", "[")):
                        raise ValueError("GPP API returned non-JSON content")
                    payload[year] = response.json()
            if any(True for _ in self._candidate_dicts(payload)):
                return json.dumps(payload)
        except Exception:
            pass

        return json.dumps({"__rendered_html__": self._render_public_page()})

    def _render_public_page(self) -> str:
        try:
            from playwright.sync_api import sync_playwright
        except Exception as exc:  # pragma: no cover - CI installs Playwright
            raise RuntimeError("GPP browser fallback unavailable") from exc

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page(
                viewport={"width": 1440, "height": 1200},
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/140 Safari/537.36",
            )
            try:
                page.goto(self.url, wait_until="domcontentloaded", timeout=45_000)
                page.wait_for_function(
                    "document.body && document.body.innerText.includes('Procuring Entity:')",
                    timeout=30_000,
                )
                page.wait_for_timeout(1_000)
                return page.content()
            finally:
                browser.close()

    def parse(self, raw: str) -> Iterable[NormalizedBid]:
        payload = json.loads(raw)
        if isinstance(payload, dict) and payload.get("__rendered_html__"):
            return self._parse_rendered_html(str(payload["__rendered_html__"]))

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
            if deadline and deadline.hour == 0 and deadline.minute == 0:
                deadline = deadline.replace(hour=23, minute=59, second=59)
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

    def _parse_rendered_html(self, raw: str) -> list[NormalizedBid]:
        soup = BeautifulSoup(raw, "html.parser")
        now = datetime.now(KAMPALA)
        discovered: dict[str, NormalizedBid] = {}
        seen_blocks: set[str] = set()

        for label in soup.find_all(string=re.compile(r"Procuring\s+Entity\s*:", re.I)):
            block = None
            node = label.parent
            for candidate in [node, *list(node.parents)[:6]]:
                text = clean(candidate.get_text(" ", strip=True))
                if "Procuring Entity:" in text and "Deadline:" in text and 40 < len(text) < 1800:
                    block = candidate
                    break
            if block is None:
                continue

            text = clean(block.get_text(" ", strip=True))
            fingerprint = re.sub(r"\s+", " ", text.lower())
            if fingerprint in seen_blocks:
                continue
            seen_blocks.add(fingerprint)

            org_match = re.search(r"Procuring\s+Entity\s*:\s*(.*?)\s+(?:Category\s*:|Type\s*:|Deadline\s*:)", text, re.I)
            category_match = re.search(r"Category\s*:\s*(.*?)\s+(?:Type\s*:|Deadline\s*:)", text, re.I)
            type_match = re.search(r"Type\s*:\s*(.*?)\s+Deadline\s*:", text, re.I)
            organization = clean(org_match.group(1)) if org_match else ""
            if not organization:
                continue

            deadline = extract_deadline(text)
            if deadline is None:
                deadline_match = re.search(r"Deadline\s*:\s*([^|]{6,40})", text, re.I)
                deadline = parse_date(deadline_match.group(1)) if deadline_match else None
            if deadline is None:
                continue
            if deadline.hour == 0 and deadline.minute == 0:
                deadline = deadline.replace(hour=23, minute=59, second=59)

            detail_anchor = block.find("a", href=re.compile(r"tender-notice", re.I))
            if detail_anchor is None:
                detail_anchor = block.find("a", string=re.compile(r"view\s+bid\s+notice", re.I))
            source_url = urljoin(self.url, str(detail_anchor.get("href", ""))) if detail_anchor else self.url

            title = ""
            for heading in block.find_all(["h2", "h3", "h4", "h5", "a", "strong"]):
                candidate = clean(heading.get_text(" ", strip=True))
                lowered = candidate.lower()
                if len(candidate) >= 12 and not any(token in lowered for token in ("view bid notice", "procuring entity", "deadline")):
                    title = candidate
                    break
            if not title:
                prefix = text.split("Procuring Entity:", 1)[0].strip()
                title = prefix[-320:].strip()
            if not title:
                continue

            procurement_type = clean(type_match.group(1)) if type_match else "Government tender"
            category = clean(category_match.group(1)) if category_match else procurement_type
            bid = NormalizedBid(
                title=title[:320],
                organization=organization[:180],
                reference_number=extract_reference(text),
                description=text[:3000],
                category=category[:120],
                procurement_type=procurement_type[:100],
                published_at=None,
                deadline_at=deadline,
                deadline_precision="date",
                status="open" if deadline >= now else "closed",
                sources=[SourceRef(name=self.name, url=source_url, detected_at=now)],
                source_metadata={"collector": "gpp-public-browser"},
            )
            discovered[bid.canonical_key()] = bid

        return list(discovered.values())

    def enrich(self, bid: NormalizedBid) -> NormalizedBid:
        if not bid.sources:
            return bid
        detail_url = str(bid.sources[0].url)
        if "tender-notice" not in detail_url:
            return bid
        try:
            response = httpx.get(
                detail_url,
                timeout=20,
                follow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0 (compatible; AutoMindsBidFinder/2.0)"},
            )
            response.raise_for_status()
            text = clean(BeautifulSoup(response.text, "html.parser").get_text(" ", strip=True))
        except Exception:
            return bid

        reference = extract_reference(text)
        if reference:
            bid.reference_number = reference
        deadline = extract_deadline(text)
        if deadline:
            if deadline.hour == 0 and deadline.minute == 0:
                deadline = deadline.replace(hour=23, minute=59, second=59)
            bid.deadline_at = deadline
            bid.deadline_precision = "datetime" if re.search(r"\d{1,2}:\d{2}", text) else "date"
        if len(text) > len(bid.description):
            bid.description = text[:5000]
        return bid

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
