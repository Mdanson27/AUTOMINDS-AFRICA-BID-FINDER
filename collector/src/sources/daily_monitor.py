from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
import hashlib
import re

from bs4 import BeautifulSoup

from .base import BidSource
from .common_web import KAMPALA, clean, extract_deadline, extract_reference, infer_type, organization_from_title, parse_date
from .newspaper_common import (
    CaptureReport,
    direct_fetch,
    discover_with_bing_rss,
    domain_matches,
    notice_urls_from_html,
    parse_notice_page,
    render_fetch,
    utc_now_iso,
)
from ..models import NormalizedBid, SourceRef


KEYWORD_RE = re.compile(
    r"\b(tender|procurement|expression(?:s)? of interest|invitation (?:to|for) (?:bid|bids)|request for (?:proposal|quotation)|pre-?qualification)\b",
    re.I,
)


class DailyMonitorSource(BidSource):
    name = "Daily Monitor"
    source_id = "daily-monitor"
    url = "https://www.monitor.co.ug/uganda/jobs/tenders"
    domain = "monitor.co.ug"
    notice_patterns = ("/uganda/jobs/tenders/",)

    def __init__(self) -> None:
        self.capture_report = CaptureReport()

    def fetch(self) -> str:
        raw, status, _ = direct_fetch(self.url)
        self.capture_report.http_status = status
        if status == 403:
            self.capture_report.source_status = "BLOCKED"
            self.capture_report.capture_status = "INCOMPLETE"
            self.capture_report.direct_status = "blocked_403"
            self.capture_report.capture_warnings.append("Direct access returned HTTP 403; records found are unknown.")
            return ""
        if status is None or status >= 400:
            self.capture_report.source_status = "DEGRADED"
            self.capture_report.capture_status = "INCOMPLETE"
            self.capture_report.direct_status = f"http_{status or 'error'}"
            return raw
        self.capture_report.direct_status = "success"
        return raw

    @staticmethod
    def _qualifying_block(container) -> tuple[str, object | None, object | None] | None:
        text = clean(container.get_text(" ", strip=True))
        if len(text) < 70 or len(text) > 6000 or not KEYWORD_RE.search(text):
            return None

        deadline = extract_deadline(text)
        reference = extract_reference(text)
        heading = container.find(["h1", "h2", "h3", "h4", "h5", "strong", "b"])
        if not deadline and not reference and heading is None:
            return None
        return text, deadline, reference

    def _generic_listing_bids(self, soup: BeautifulSoup, now: datetime) -> list[NormalizedBid]:
        candidates = []
        seen_text: set[str] = set()

        # Prefer the smallest qualifying DOM block. This avoids turning a parent
        # page wrapper containing many tenders into one giant false notice.
        for container in soup.find_all(["article", "li", "section", "div"]):
            qualified = self._qualifying_block(container)
            if qualified is None:
                continue
            text, deadline, reference = qualified
            digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
            if digest in seen_text:
                continue

            child_has_notice = False
            for child in container.find_all(["article", "li", "section", "div"], recursive=False):
                if self._qualifying_block(child) is not None:
                    child_has_notice = True
                    break
            if child_has_notice:
                continue

            heading = container.find(["h1", "h2", "h3", "h4", "h5", "strong", "b"])
            title = clean(heading.get_text(" ", strip=True)) if heading else ""
            if len(title) < 12:
                # Monitor listing entries often lead with the procurement title,
                # followed by a sentence describing the entity and deadline.
                title = re.split(r"(?<=[.!?])\s+|\s{2,}", text, maxsplit=1)[0][:320]
            if len(title) < 12 or len(title) > 320:
                continue

            procurement_type = infer_type(title, text)
            verification = "VERIFIED" if reference and deadline else "MANUAL_REVIEW"
            candidates.append(
                NormalizedBid(
                    title=title,
                    organization=organization_from_title(title),
                    reference_number=reference or "",
                    description=text[:4000],
                    category=procurement_type,
                    procurement_type=procurement_type,
                    published_at=None,
                    deadline_at=deadline,
                    deadline_precision="datetime" if deadline else "unknown",
                    status="open" if deadline is None or deadline >= now else "closed",
                    sources=[SourceRef(name=self.name, url=self.url, detected_at=now)],
                    source_metadata={
                        "captureSurface": "publisher-tender-listing-generic-block",
                        "canonicalPublisher": self.name,
                        "verification": verification,
                    },
                )
            )
            seen_text.add(digest)

        unique: dict[str, NormalizedBid] = {}
        for bid in candidates:
            unique[bid.canonical_key()] = bid
        return list(unique.values())

    def parse(self, raw: str) -> Iterable[NormalizedBid]:
        soup = BeautifulSoup(raw, "html.parser")
        now = datetime.now(KAMPALA)
        discovered: dict[str, NormalizedBid] = {}

        for anchor in soup.find_all("a", href=True):
            href = str(anchor.get("href", ""))
            if href.startswith("/"):
                href = "https://www.monitor.co.ug" + href
            if not domain_matches(href, self.domain) or "/uganda/jobs/tenders/" not in href:
                continue
            if href.rstrip("/") == self.url.rstrip("/"):
                continue
            title = clean(anchor.get_text(" ", strip=True))
            if len(title) < 12:
                continue

            container = anchor.find_parent(["article", "li"]) or anchor.find_parent("div")
            text = clean(container.get_text(" ", strip=True) if container else title)
            deadline = extract_deadline(text)
            published = None
            time_node = container.find("time") if container else None
            if time_node is not None:
                published = parse_date(str(time_node.get("datetime") or time_node.get_text(" ", strip=True)))
            procurement_type = infer_type(title, text)
            bid = NormalizedBid(
                title=title,
                organization=organization_from_title(title),
                reference_number=extract_reference(text),
                description=text[:1800],
                category=procurement_type,
                procurement_type=procurement_type,
                published_at=published,
                deadline_at=deadline,
                deadline_precision="datetime" if deadline else "unknown",
                status="open" if deadline is None or deadline >= now else "closed",
                sources=[SourceRef(name=self.name, url=href, detected_at=now)],
                source_metadata={"captureSurface": "linked-listing-item", "canonicalPublisher": self.name},
            )
            discovered[bid.canonical_key()] = bid

        for bid in self._generic_listing_bids(soup, now):
            discovered[bid.canonical_key()] = bid
        return list(discovered.values())

    def collect(self) -> list[NormalizedBid]:
        report = CaptureReport(started_at=utc_now_iso())
        self.capture_report = report
        candidates: list[str] = []
        normalized: dict[str, NormalizedBid] = {}

        def absorb_listing(raw: str) -> None:
            for bid in self.parse(raw):
                key = bid.canonical_key()
                if key in normalized:
                    report.duplicates += 1
                else:
                    report.records_extracted += 1
                normalized[key] = bid

        direct_raw, status, final_url = direct_fetch(self.url)
        report.http_status = status
        if status == 403:
            report.source_status = "BLOCKED"
            report.capture_status = "INCOMPLETE"
            report.direct_status = "blocked_403"
            report.capture_warnings.append("Direct category fetch returned HTTP 403; records found are UNKNOWN, not zero.")
        elif status is not None and status < 400:
            report.direct_status = "success"
            absorb_listing(direct_raw)
            candidates.extend(notice_urls_from_html(direct_raw, final_url, self.domain, self.notice_patterns))
        else:
            report.direct_status = f"http_{status or 'error'}"
            report.capture_warnings.append("Direct category fetch failed.")

        rendered_raw, render_status = render_fetch(self.url)
        report.render_status = render_status
        if rendered_raw:
            absorb_listing(rendered_raw)
            candidates.extend(notice_urls_from_html(rendered_raw, self.url, self.domain, self.notice_patterns))

        discovered = discover_with_bing_rss(self.domain)
        report.discovery_status = "active" if discovered else "no_results"
        candidates.extend(discovered)
        candidates = [
            url for url in dict.fromkeys(candidates)
            if domain_matches(url, self.domain)
            and "/uganda/jobs/tenders/" in url
            and url.rstrip("/") != self.url.rstrip("/")
        ]
        report.urls_discovered = len(candidates)
        report.discovery_method = "direct+browser+publisher_listing+generic_blocks+domain_search"

        for url in candidates:
            raw, page_status, final_url = direct_fetch(url)
            if page_status is None or page_status >= 400 or not domain_matches(final_url, self.domain):
                report.records_rejected += 1
                continue
            report.urls_fetched += 1
            bid = parse_notice_page(raw, final_url, self.name, self.domain)
            if bid is None:
                report.records_rejected += 1
                continue
            report.records_extracted += 1
            key = bid.canonical_key()
            if key in normalized:
                report.duplicates += 1
            normalized[key] = bid

        report.records_normalized = len(normalized)
        for bid in normalized.values():
            verification = bid.source_metadata.get("verification", "MANUAL_REVIEW")
            if verification == "VERIFIED":
                report.verified += 1
            else:
                report.review_required += 1

        if report.records_normalized:
            report.source_status = "DEGRADED" if status == 403 else "HEALTHY"
            report.capture_status = "PARTIAL" if status == 403 or render_status != "success" else "SUCCESS"
        elif status == 403:
            report.source_status = "BLOCKED"
            report.capture_status = "INCOMPLETE"
        else:
            report.source_status = "DEGRADED"
            report.capture_status = "PARTIAL"
            report.capture_warnings.append("No newspaper notices could be verified; record count remains UNKNOWN.")

        report.completed_at = utc_now_iso()
        return list(normalized.values())
