from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from html import unescape
import hashlib
import re
from urllib.parse import parse_qs, quote_plus, urlparse
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup
import httpx

from .common_web import KAMPALA, clean, extract_deadline, extract_reference, infer_type, organization_from_title, parse_date
from ..models import NormalizedBid, SourceDocument, SourceRef


KEYWORDS = (
    "tender",
    "procurement",
    "invitation to bid",
    "invitation for bids",
    "expression of interest",
    "request for proposal",
    "request for quotation",
    "prequalification",
    "pre-qualification",
    "supplier prequalification",
)


@dataclass
class CaptureReport:
    source_status: str = "UNKNOWN"
    capture_status: str = "INCOMPLETE"
    http_status: int | None = None
    discovery_method: str = "direct"
    urls_discovered: int = 0
    urls_fetched: int = 0
    records_extracted: int = 0
    records_normalized: int = 0
    records_rejected: int = 0
    duplicates: int = 0
    updates: int = 0
    parser_errors: int = 0
    capture_warnings: list[str] = field(default_factory=list)
    started_at: str = ""
    completed_at: str = ""
    direct_status: str = "not_attempted"
    render_status: str = "not_attempted"
    discovery_status: str = "not_attempted"
    review_required: int = 0
    verified: int = 0

    def as_source_meta(self) -> dict[str, object]:
        return {
            "collectorStatus": self.source_status,
            "captureStatus": self.capture_status,
            "httpStatus": self.http_status,
            "discoveryMethod": self.discovery_method,
            "urlsDiscovered": self.urls_discovered,
            "urlsSuccessfullyFetched": self.urls_fetched,
            "recordsExtracted": self.records_extracted,
            "recordsNormalized": self.records_normalized,
            "recordsRejected": self.records_rejected,
            "duplicates": self.duplicates,
            "updates": self.updates,
            "parserErrors": self.parser_errors,
            "captureWarnings": self.capture_warnings,
            "directStatus": self.direct_status,
            "renderStatus": self.render_status,
            "discoveryStatus": self.discovery_status,
            "needsReview": self.review_required,
            "verifiedRecords": self.verified,
        }


def utc_now_iso() -> str:
    return datetime.now(KAMPALA).isoformat()


def domain_matches(url: str, allowed_domain: str) -> bool:
    host = (urlparse(url).hostname or "").lower().lstrip("www.")
    allowed = allowed_domain.lower().lstrip("www.")
    return host == allowed or host.endswith("." + allowed)


def direct_fetch(url: str) -> tuple[str, int | None, str]:
    try:
        response = httpx.get(
            url,
            timeout=45,
            follow_redirects=True,
            headers={
                "User-Agent": "AutoMindsBidFinder/1.0 (+public procurement indexing; Uganda)",
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        return response.text, response.status_code, str(response.url)
    except httpx.HTTPError:
        return "", None, url


def render_fetch(url: str) -> tuple[str, str]:
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return "", "unavailable"

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="networkidle", timeout=60000)
            html = page.content()
            browser.close()
            return html, "success"
    except Exception:
        return "", "failed"


def looks_incomplete_html(raw: str) -> bool:
    text = clean(BeautifulSoup(raw or "", "html.parser").get_text(" ", strip=True)).lower()
    if not text:
        return True
    return any(marker in text for marker in ("loading data", "no articles available"))


def discover_with_bing_rss(domain: str, recent_days: int = 30) -> list[str]:
    query = (
        f"site:{domain} (tender OR procurement OR bid OR \"expression of interest\" "
        f"OR prequalification OR \"invitation to bid\")"
    )
    url = f"https://www.bing.com/search?format=rss&q={quote_plus(query)}&freshness=Month"
    try:
        response = httpx.get(
            url,
            timeout=30,
            follow_redirects=True,
            headers={"User-Agent": "AutoMindsBidFinder/1.0 (+public procurement discovery; Uganda)"},
        )
        response.raise_for_status()
        root = ET.fromstring(response.text)
    except Exception:
        return []

    found: list[str] = []
    for item in root.findall(".//item"):
        link = clean(item.findtext("link") or "")
        if not link:
            continue
        parsed = urlparse(link)
        if parsed.hostname and domain_matches(link, domain):
            found.append(link)
            continue
        qs = parse_qs(parsed.query)
        for candidate in qs.get("url", []) + qs.get("u", []):
            candidate = unescape(candidate)
            if domain_matches(candidate, domain):
                found.append(candidate)
    return list(dict.fromkeys(found))


def notice_urls_from_html(raw: str, base_url: str, allowed_domain: str, patterns: tuple[str, ...]) -> list[str]:
    from urllib.parse import urljoin

    soup = BeautifulSoup(raw or "", "html.parser")
    urls: list[str] = []
    for anchor in soup.find_all("a", href=True):
        href = urljoin(base_url, str(anchor.get("href", "")))
        if not domain_matches(href, allowed_domain):
            continue
        if any(pattern in href for pattern in patterns):
            urls.append(href)
    return list(dict.fromkeys(urls))


def parse_notice_page(
    raw: str,
    url: str,
    source_name: str,
    allowed_domain: str,
) -> NormalizedBid | None:
    if not raw or not domain_matches(url, allowed_domain):
        return None
    soup = BeautifulSoup(raw, "html.parser")
    now = datetime.now(KAMPALA)

    title_node = soup.find("h1") or soup.find("h2")
    title = clean(title_node.get_text(" ", strip=True)) if title_node else ""
    if not title:
        meta = soup.find("meta", attrs={"property": "og:title"})
        title = clean(str(meta.get("content", ""))) if meta else ""

    main = soup.find("article") or soup.find("main") or soup.body
    text = clean(main.get_text(" ", strip=True) if main else soup.get_text(" ", strip=True))
    if not title or len(title) < 8 or not any(keyword in (title + " " + text).lower() for keyword in KEYWORDS):
        return None

    deadline = extract_deadline(text)
    published = None
    time_node = soup.find("time")
    if time_node is not None:
        published = parse_date(str(time_node.get("datetime") or time_node.get_text(" ", strip=True)))

    procurement_type = infer_type(title, text)
    organization = organization_from_title(title)

    documents: list[SourceDocument] = []
    for anchor in soup.find_all("a", href=True):
        href = str(anchor.get("href", ""))
        absolute = httpx.URL(url).join(href)
        lower = str(absolute).lower()
        if lower.endswith((".pdf", ".doc", ".docx", ".xls", ".xlsx", ".jpg", ".jpeg", ".png")):
            label = clean(anchor.get_text(" ", strip=True)) or "Linked procurement document"
            kind = lower.rsplit(".", 1)[-1]
            try:
                documents.append(SourceDocument(title=label[:180], url=str(absolute), kind=kind))
            except Exception:
                continue

    evidence_fields = [bool(title), bool(organization), bool(extract_reference(text)), bool(deadline), True]
    confidence = sum(evidence_fields) / len(evidence_fields)
    verification = "VERIFIED" if confidence >= 0.8 else "MANUAL_REVIEW"
    fingerprint = hashlib.sha256((url + "|" + title + "|" + text[:2000]).encode("utf-8")).hexdigest()[:20]

    return NormalizedBid(
        title=title,
        organization=organization,
        reference_number=extract_reference(text),
        description=text[:4000],
        category=procurement_type,
        procurement_type=procurement_type,
        published_at=published,
        deadline_at=deadline,
        deadline_precision="datetime" if deadline else "unknown",
        status="open" if deadline is None or deadline >= now else "closed",
        sources=[SourceRef(name=source_name, url=url, detected_at=now)],
        source_metadata={
            "extractionConfidence": f"{confidence:.2f}",
            "verification": verification,
            "pageFingerprint": fingerprint,
            "canonicalPublisher": source_name,
        },
        documents=documents,
    )
