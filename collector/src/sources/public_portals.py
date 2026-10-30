from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
import httpx

from .base import BidSource
from .common_web import KAMPALA, clean, extract_deadline, extract_reference, infer_type, parse_date
from ..models import NormalizedBid, SourceRef


USER_AGENT = "Mozilla/5.0 (compatible; AutoMindsBidFinder/2.0; +https://automindsafrica.com)"
OPPORTUNITY_TERMS = (
    "tender",
    "bid notice",
    "invitation to bid",
    "invitation for bids",
    "invitation to tender",
    "request for proposal",
    "request for quotation",
    "expression of interest",
    "prequalification",
    "pre-qualification",
    "procurement",
    "framework agreement",
    "solicitation",
    "call for tenders",
)
IGNORE_TITLE_TERMS = (
    "career",
    "vacancy",
    "job opening",
    "employment",
    "read more",
    "learn more",
    "privacy",
    "cookie",
)
DATE_TOKEN = (
    r"(?:\d{1,2}(?:st|nd|rd|th)?[\s,./-]+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)[\s,./-]+20\d{2}"
    r"|(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2}(?:st|nd|rd|th)?,?\s+20\d{2}"
    r"|\d{1,2}[./-]\d{1,2}[./-]20\d{2}"
    r"|20\d{2}[-/]\d{1,2}[-/]\d{1,2})"
)
DATE_PATTERN = re.compile(DATE_TOKEN, re.I)
PUBLISHED_PATTERN = re.compile(
    rf"(?:published(?:\s+on)?|publication\s+date|date\s+published|posted(?:\s+on)?|date\s+posted|issue\s+date)\s*[:\-]?\s*({DATE_TOKEN})",
    re.I,
)
TIME_PATTERN = re.compile(r"\b\d{1,2}:\d{2}\s*(?:am|pm|hrs?|hours?)?\b|\b\d{1,2}\s*(?:am|pm)\b", re.I)


@dataclass(frozen=True)
class PortalConfig:
    source_id: str
    name: str
    url: str
    organization: str
    source_type: str = "development"
    country_terms: tuple[str, ...] = ()


class PublicProcurementPortalSource(BidSource):
    """Conservative parser for public procurement/tender listing pages.

    The adapter only emits records when it can identify procurement intent and
    an explicit closing/deadline/submission date. It deliberately refuses to
    guess a deadline from an unlabeled date such as a publication date. Sources
    that need more specialized extraction stay monitored but cannot contaminate
    the live opportunity feed with an inferred deadline.
    """

    def __init__(self, config: PortalConfig):
        self.config = config
        self.source_id = config.source_id
        self.name = config.name
        self.url = config.url
        self.organization = config.organization
        self.source_type = config.source_type

    def fetch(self) -> str:
        response = httpx.get(
            self.url,
            timeout=18,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
        )
        response.raise_for_status()
        return response.text

    def _country_matches(self, text: str) -> bool:
        if not self.config.country_terms:
            return True
        lowered = text.lower()
        return any(term.lower() in lowered for term in self.config.country_terms)

    @staticmethod
    def _end_of_day_if_date_only(value: datetime, text: str) -> datetime:
        if value.hour == 0 and value.minute == 0 and not TIME_PATTERN.search(text):
            return value.replace(hour=23, minute=59, second=59, microsecond=0)
        return value

    @classmethod
    def _deadline(cls, text: str) -> datetime | None:
        # Accuracy over coverage: never infer a closing deadline from an
        # unlabeled date. The shared extractor accepts only explicit deadline,
        # closing, submission, "before", or equivalent procurement wording.
        direct = extract_deadline(text)
        return cls._end_of_day_if_date_only(direct, text) if direct else None

    @classmethod
    def _published(cls, text: str, deadline: datetime | None) -> datetime | None:
        # Publication timestamps are optional. Only trust explicitly-labelled
        # publication/posted/issue dates; never use "the earliest date on the
        # card", which can be a schedule date from an unrelated field.
        match = PUBLISHED_PATTERN.search(text)
        if not match:
            return None
        parsed = parse_date(match.group(1))
        if not parsed or (deadline is not None and parsed > deadline):
            return None
        return parsed

    @staticmethod
    def _title_from_block(block) -> str:
        for node in block.find_all(["h1", "h2", "h3", "h4", "h5", "strong", "a"], limit=12):
            value = clean(node.get_text(" ", strip=True))
            lowered = value.lower()
            if len(value) < 14 or any(term in lowered for term in IGNORE_TITLE_TERMS):
                continue
            if any(term in lowered for term in OPPORTUNITY_TERMS) or len(value) >= 28:
                return value[:320]
        return ""

    def _candidate_blocks(self, soup: BeautifulSoup):
        seen: set[int] = set()
        blocks = []
        for node in soup.find_all(["article", "tr", "li", "section", "div"]):
            text = clean(node.get_text(" ", strip=True))
            lowered = text.lower()
            if len(text) < 40 or len(text) > 5000:
                continue
            if not any(term in lowered for term in OPPORTUNITY_TERMS):
                continue
            if not self._country_matches(text):
                continue
            identity = id(node)
            if identity in seen:
                continue
            seen.add(identity)
            blocks.append(node)
            if len(blocks) >= 120:
                break
        return blocks

    def parse(self, raw: str):
        soup = BeautifulSoup(raw, "html.parser")
        now = datetime.now(KAMPALA)
        discovered: dict[str, NormalizedBid] = {}

        for block in self._candidate_blocks(soup):
            text = clean(block.get_text(" ", strip=True))
            deadline = self._deadline(text)
            if deadline is None or deadline < now:
                continue

            title = self._title_from_block(block)
            if not title:
                continue
            lowered_title = title.lower()
            if any(term in lowered_title for term in IGNORE_TITLE_TERMS):
                continue

            anchor = block.find("a", href=True)
            href = urljoin(self.url, anchor.get("href", "")) if anchor else self.url
            if href.startswith("mailto:") or href.startswith("javascript:"):
                href = self.url
            reference = extract_reference(text)
            published = self._published(text, deadline)
            procurement_type = infer_type(title, text)

            bid = NormalizedBid(
                title=title,
                organization=self.organization,
                reference_number=reference,
                description=text[:2800],
                category=procurement_type,
                procurement_type=procurement_type,
                published_at=published,
                deadline_at=deadline,
                deadline_precision="datetime" if TIME_PATTERN.search(text) else "date",
                status="open",
                sources=[SourceRef(name=self.name, url=href, detected_at=now)],
                source_metadata={"collector": "public-portal", "sourceType": self.source_type},
            )
            discovered[bid.canonical_key()] = bid

        return list(discovered.values())

    def enrich(self, bid: NormalizedBid) -> NormalizedBid:
        source_url = str(bid.sources[0].url) if bid.sources else self.url
        if source_url == self.url or urlparse(source_url).scheme not in {"http", "https"}:
            return bid
        try:
            response = httpx.get(
                source_url,
                timeout=15,
                follow_redirects=True,
                headers={"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"},
            )
            response.raise_for_status()
            text = clean(BeautifulSoup(response.text, "html.parser").get_text(" ", strip=True))
        except Exception:
            return bid

        deadline = self._deadline(text)
        if deadline:
            bid.deadline_at = deadline
            bid.deadline_precision = "datetime" if TIME_PATTERN.search(text) else "date"
        reference = extract_reference(text)
        if reference:
            bid.reference_number = reference
        published = self._published(text, bid.deadline_at)
        if published:
            bid.published_at = published
        if len(text) > len(bid.description):
            bid.description = text[:4000]
        return bid


PUBLIC_PORTAL_CONFIGS = (
    PortalConfig("giz-uganda", "GIZ Uganda", "https://www.giz.de/en/regions/africa/uganda/tenders", "GIZ Uganda", "development"),
    PortalConfig("ungm-uganda", "UN Global Marketplace", "https://www.ungm.org/Public/Notice", "United Nations", "development", ("uganda", "kampala")),
    PortalConfig("unicef-uganda", "UNICEF Uganda", "https://www.unicef.org/uganda/procurement", "UNICEF Uganda", "development", ("uganda", "kampala")),
    PortalConfig("unhcr-uganda", "UNHCR", "https://www.unhcr.org/get-involved/work-us/become-supplier/bidding-opportunities", "UNHCR", "development", ("uganda", "kampala")),
    PortalConfig("wfp-uganda", "World Food Programme", "https://www.wfp.org/do-business-with-wfp", "World Food Programme", "development", ("uganda", "kampala")),
    PortalConfig("enabel-uganda", "Enabel Uganda", "https://www.enabel.be/list-public-procurement/", "Enabel Uganda", "development", ("uganda",)),
    PortalConfig("eu-delegation-uganda", "EU Delegation to Uganda", "https://www.eeas.europa.eu/eeas/tenders_en", "Delegation of the European Union to Uganda", "development", ("uganda", "kampala")),
    PortalConfig("irc-uganda", "International Rescue Committee", "https://www.rescue.org/procurement-policies-and-bid-opportunities", "International Rescue Committee", "ngo", ("uganda", "kampala", "2ua")),
    PortalConfig("world-vision-uganda", "World Vision Uganda", "https://www.wvi.org/uganda/tenders", "World Vision Uganda", "ngo"),
    PortalConfig("uganda-red-cross", "Uganda Red Cross Society", "https://redcrossug.org/jobs/", "Uganda Red Cross Society", "ngo"),
    PortalConfig("ucaa", "Uganda Civil Aviation Authority", "https://caa.go.ug/available-bids-tenders/", "Uganda Civil Aviation Authority", "government"),
    PortalConfig("nssf-uganda", "NSSF Uganda", "https://nssfug.org/opportunities/tenders/", "National Social Security Fund Uganda", "government"),
    PortalConfig("bank-of-uganda", "Bank of Uganda", "https://www.bou.or.ug/procurement", "Bank of Uganda", "government"),
    PortalConfig("era-uganda", "Electricity Regulatory Authority", "https://www.era.go.ug/procurement-tenders/", "Electricity Regulatory Authority", "government"),
    PortalConfig("uetcl", "Uganda Electricity Transmission Company", "https://uetcl.go.ug/tenders-bids/", "Uganda Electricity Transmission Company Limited", "government"),
    PortalConfig("uganda-development-bank", "Uganda Development Bank", "https://www.udbl.co.ug/bids-tenders/", "Uganda Development Bank", "government"),
    PortalConfig("nwsc", "National Water & Sewerage Corporation", "https://www.nwsc.co.ug/notices-2/", "National Water & Sewerage Corporation", "government"),
    PortalConfig("save-the-children-uganda", "Save the Children", "https://www.savethechildren.net/tenders", "Save the Children International", "ngo", ("uganda", "kampala")),
)

PUBLIC_PORTAL_SOURCES = tuple(PublicProcurementPortalSource(config) for config in PUBLIC_PORTAL_CONFIGS)
PUBLIC_SOURCE_TYPES = {config.source_id: config.source_type for config in PUBLIC_PORTAL_CONFIGS}
