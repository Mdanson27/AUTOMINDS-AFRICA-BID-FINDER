from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

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
            )
            discovered[bid.canonical_key()] = bid
        return list(discovered.values())

    def collect(self) -> list[NormalizedBid]:
        report = CaptureReport(started_at=utc_now_iso())
        self.capture_report = report
        candidates: list[str] = []
        normalized: dict[str, NormalizedBid] = {}

        direct_raw, status, final_url = direct_fetch(self.url)
        report.http_status = status
        if status == 403:
            report.source_status = "BLOCKED"
            report.capture_status = "INCOMPLETE"
            report.direct_status = "blocked_403"
            report.capture_warnings.append("Direct category fetch returned HTTP 403; records found are UNKNOWN, not zero.")
        elif status is not None and status < 400:
            report.direct_status = "success"
            candidates.extend(notice_urls_from_html(direct_raw, final_url, self.domain, self.notice_patterns))
        else:
            report.direct_status = f"http_{status or 'error'}"
            report.capture_warnings.append("Direct category fetch failed.")

        rendered_raw, render_status = render_fetch(self.url)
        report.render_status = render_status
        if rendered_raw:
            candidates.extend(notice_urls_from_html(rendered_raw, self.url, self.domain, self.notice_patterns))

        discovered = discover_with_bing_rss(self.domain)
        report.discovery_status = "active" if discovered else "no_results"
        candidates.extend(discovered)
        candidates = [url for url in dict.fromkeys(candidates) if domain_matches(url, self.domain)]
        report.urls_discovered = len(candidates)
        report.discovery_method = "direct+browser+domain_search"

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
