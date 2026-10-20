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
    looks_incomplete_html,
    notice_urls_from_html,
    parse_notice_page,
    render_fetch,
    utc_now_iso,
)
from ..models import NormalizedBid, SourceRef


class NewVisionSource(BidSource):
    name = "New Vision"
    source_id = "new-vision"
    url = "https://www.newvision.co.ug/opportunities/tenders"
    listing_url = "https://www.newvision.co.ug/opportunities/tenders-1250"
    domain = "newvision.co.ug"
    notice_patterns = ("/opportunities/tenders-", "/opportunities/notices-")

    def __init__(self) -> None:
        self.capture_report = CaptureReport()

    def fetch(self) -> str:
        raw, status, _ = direct_fetch(self.url)
        self.capture_report.http_status = status
        if status is None or status >= 400:
            self.capture_report.source_status = "DEGRADED"
            self.capture_report.capture_status = "INCOMPLETE"
            self.capture_report.direct_status = f"http_{status or 'error'}"
            return raw
        self.capture_report.direct_status = "success"
        if looks_incomplete_html(raw):
            self.capture_report.source_status = "DEGRADED"
            self.capture_report.capture_status = "INCOMPLETE"
            self.capture_report.capture_warnings.append("Category page returned dynamic/empty shell; record count is UNKNOWN.")
        return raw

    def parse(self, raw: str) -> Iterable[NormalizedBid]:
        soup = BeautifulSoup(raw, "html.parser")
        now = datetime.now(KAMPALA)
        discovered: dict[str, NormalizedBid] = {}

        for anchor in soup.find_all("a", href=True):
            href = str(anchor.get("href", ""))
            if href.startswith("/"):
                href = "https://www.newvision.co.ug" + href
            if not domain_matches(href, self.domain):
                continue
            if not any(pattern in href for pattern in self.notice_patterns):
                continue
            if href.rstrip("/") in {self.url.rstrip("/"), self.listing_url.rstrip("/")}:
                continue
            title = clean(anchor.get("title") or anchor.get_text(" ", strip=True))
            if len(title) < 10:
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
                source_metadata={"captureSurface": "publisher-listing", "canonicalPublisher": self.name},
            )
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
        direct_incomplete = status is None or status >= 400 or looks_incomplete_html(direct_raw)
        if status is not None and status < 400:
            report.direct_status = "dynamic_or_empty" if direct_incomplete else "success"
            absorb_listing(direct_raw)
            candidates.extend(notice_urls_from_html(direct_raw, final_url, self.domain, self.notice_patterns))
        else:
            report.direct_status = f"http_{status or 'error'}"
        if direct_incomplete:
            report.capture_warnings.append("Direct category response was incomplete/dynamic; zero records must not be treated as a genuine zero.")

        rendered_raw, render_status = render_fetch(self.url)
        report.render_status = render_status
        if rendered_raw:
            absorb_listing(rendered_raw)
            candidates.extend(notice_urls_from_html(rendered_raw, self.url, self.domain, self.notice_patterns))

        # New Vision currently exposes a stable publisher-owned tenders listing
        # even when the short /opportunities/tenders route renders an empty shell.
        listing_raw, listing_status, listing_final = direct_fetch(self.listing_url)
        if listing_status is not None and listing_status < 400:
            absorb_listing(listing_raw)
            candidates.extend(notice_urls_from_html(listing_raw, listing_final, self.domain, self.notice_patterns))
        listing_rendered, listing_render_status = render_fetch(self.listing_url)
        if listing_rendered:
            absorb_listing(listing_rendered)
            candidates.extend(notice_urls_from_html(listing_rendered, self.listing_url, self.domain, self.notice_patterns))
        if listing_status is None or listing_status >= 400:
            report.capture_warnings.append("New Vision publisher listing fallback was not directly reachable.")
        if listing_render_status == "failed":
            report.capture_warnings.append("New Vision publisher listing browser render failed.")

        discovered = discover_with_bing_rss(self.domain)
        report.discovery_status = "active" if discovered else "no_results"
        candidates.extend(discovered)
        candidates = [
            url for url in dict.fromkeys(candidates)
            if domain_matches(url, self.domain)
            and any(pattern in url for pattern in self.notice_patterns)
            and url.rstrip("/") not in {self.url.rstrip("/"), self.listing_url.rstrip("/")}
        ]
        report.urls_discovered = len(candidates)
        report.discovery_method = "direct+browser+publisher_listing+domain_search"

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
            report.source_status = "PARTIAL" if direct_incomplete or render_status != "success" else "HEALTHY"
            report.capture_status = "PARTIAL" if direct_incomplete or render_status != "success" else "SUCCESS"
        else:
            report.source_status = "DEGRADED"
            report.capture_status = "PARSER_FAILURE" if candidates else "INCOMPLETE"
            report.capture_warnings.append("No original New Vision notice could be normalized; record count remains UNKNOWN.")

        report.completed_at = utc_now_iso()
        return list(normalized.values())
