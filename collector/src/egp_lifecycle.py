from __future__ import annotations

from datetime import datetime
import re
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup


KAMPALA = ZoneInfo("Africa/Kampala")
BEB_LIST_URL = "https://egpuganda.go.ug/best-evaluated-bidder-notice-reports"
CONTRACTS_LIST_URL = "https://egpuganda.go.ug/contracts-awarded"


def clean(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").replace("\xa0", " ")).strip()


def normalized_label(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", " ", clean(value).lower()).strip()


def parse_datetime(value: object) -> datetime | None:
    text = clean(value)
    if not text:
        return None
    candidates = [text]
    match = re.search(
        r"(\d{1,2}[/-]\d{1,2}[/-]\d{4}|\d{4}[/-]\d{1,2}[/-]\d{1,2}|\d{1,2}\s+[A-Za-z]+\s+\d{4})(?:\s+(?:at\s+)?(\d{1,2}:\d{2}(?::\d{2})?))?",
        text,
        flags=re.I,
    )
    if match:
        candidates.insert(0, " ".join(part for part in match.groups() if part))
    for candidate in candidates:
        for fmt in (
            "%d-%m-%Y %H:%M",
            "%d/%m/%Y %H:%M",
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d %H:%M",
            "%d %b %Y %H:%M",
            "%d %B %Y %H:%M",
            "%d-%m-%Y",
            "%d/%m/%Y",
            "%Y-%m-%d",
            "%d %b %Y",
            "%d %B %Y",
        ):
            try:
                return datetime.strptime(candidate, fmt).replace(tzinfo=KAMPALA)
            except ValueError:
                continue
    return None


def iso(value: datetime | None) -> str:
    return value.isoformat() if value else ""


def metadata_from_two_column_tables(soup: BeautifulSoup) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for table in soup.find_all("table"):
        for row in table.find_all("tr"):
            cells = row.find_all(["td", "th"])
            if len(cells) != 2:
                continue
            label = clean(cells[0].get_text(" ", strip=True)).rstrip(":")
            value = clean(cells[1].get_text(" ", strip=True))
            if label and value and len(label) <= 110:
                metadata[label] = value
    return metadata


def metadata_value(metadata: dict[str, str], *labels: str) -> str:
    wanted = {normalized_label(label) for label in labels}
    for key, value in metadata.items():
        if normalized_label(key) in wanted and clean(value):
            return clean(value)
    return ""


def split_name_address(value: str) -> tuple[str, str]:
    text = clean(value)
    if not text:
        return "", ""
    match = re.match(r"^(.*?)\s*\((.+)\)\s*$", text)
    if match:
        return clean(match.group(1)), clean(match.group(2))
    return text, ""


def currency_from_amount(value: str) -> str:
    match = re.search(r"\b(UGX|USD|EUR|GBP|KES|TZS)\b", value.upper())
    return match.group(1) if match else ""


def parse_bidders(soup: BeautifulSoup) -> list[dict]:
    bidders: list[dict] = []
    for table in soup.find_all("table"):
        rows = table.find_all("tr")
        if not rows:
            continue
        headers = [clean(cell.get_text(" ", strip=True)) for cell in rows[0].find_all("th")]
        normalized = [normalized_label(item) for item in headers]
        if not headers:
            continue
        name_index = next((i for i, h in enumerate(normalized) if "name" in h and "bidder" in h), None)
        if name_index is None:
            continue
        amount_index = next((i for i, h in enumerate(normalized) if "amount" in h or "price" in h), None)
        submission_index = next((i for i, h in enumerate(normalized) if "submission" in h and "date" in h), None)
        rank_index = next((i for i, h in enumerate(normalized) if "rank" in h), None)
        status_index = next((i for i, h in enumerate(normalized) if h == "status" or "status" in h), None)
        stage_index = next((i for i, h in enumerate(normalized) if "evaluation stage" in h), None)
        reason_index = next((i for i, h in enumerate(normalized) if "reason" in h), None)

        for row in rows[1:]:
            cells = row.find_all("td")
            if len(cells) <= name_index:
                continue
            raw_name = clean(cells[name_index].get_text(" ", strip=True))
            name, address = split_name_address(raw_name)
            if not name:
                continue
            amount = clean(cells[amount_index].get_text(" ", strip=True)) if amount_index is not None and len(cells) > amount_index else ""
            submission = clean(cells[submission_index].get_text(" ", strip=True)) if submission_index is not None and len(cells) > submission_index else ""
            rank = clean(cells[rank_index].get_text(" ", strip=True)) if rank_index is not None and len(cells) > rank_index else ""
            status = clean(cells[status_index].get_text(" ", strip=True)) if status_index is not None and len(cells) > status_index else ""
            stage = clean(cells[stage_index].get_text(" ", strip=True)) if stage_index is not None and len(cells) > stage_index else ""
            reasons: list[str] = []
            if reason_index is not None and len(cells) > reason_index:
                cell = cells[reason_index]
                reasons = [clean(node.get_text(" ", strip=True)) for node in cell.find_all("li") if clean(node.get_text(" ", strip=True))]
                if not reasons:
                    reason = clean(cell.get_text(" ", strip=True))
                    if reason:
                        reasons = [reason]
            bidders.append({
                "name": name,
                "address": address,
                "submissionAt": iso(parse_datetime(submission)),
                "amount": amount,
                "currency": currency_from_amount(amount),
                "rank": rank,
                "status": status,
                "evaluationStage": stage,
                "reasons": reasons,
            })
    return bidders


def _individual_links(html: str, base_url: str, tokens: tuple[str, ...]) -> list[str]:
    soup = BeautifulSoup(html, "html.parser")
    links: list[str] = []
    seen: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        href = urljoin(base_url, str(anchor.get("href") or ""))
        lower = href.lower()
        if any(token in lower for token in tokens) and href not in seen:
            seen.add(href)
            links.append(href)
    return links


def parse_beb_detail(html: str, url: str) -> dict | None:
    soup = BeautifulSoup(html, "html.parser")
    metadata = metadata_from_two_column_tables(soup)
    reference = metadata_value(metadata, "Procurement Reference Number", "Procurement Ref Number")
    title = metadata_value(metadata, "Subject of Procurement")
    organization = metadata_value(metadata, "Procurement Entity", "Procuring Entity")
    if not reference or not title:
        return None

    method = metadata_value(metadata, "Method of Procurement", "Procurement Method")
    best = metadata_value(metadata, "Name of Best Evaluated Bidder")
    amount = metadata_value(metadata, "Total Contract Price", "Contract Price")
    display_date = parse_datetime(metadata_value(metadata, "Date for Display", "Published on"))
    bidders = parse_bidders(soup)

    if best and not any(clean(item.get("name")).lower() == best.lower() for item in bidders):
        bidders.insert(0, {
            "name": best,
            "address": "",
            "submissionAt": "",
            "amount": amount,
            "currency": currency_from_amount(amount),
            "rank": "1",
            "status": "Best evaluated bidder",
            "evaluationStage": "Best evaluated bidder notice",
            "reasons": [],
        })

    return {
        "referenceNumber": reference,
        "organization": organization,
        "title": title,
        "procurementMethod": method,
        "status": "evaluation",
        "sourceStage": "Evaluation / BEB",
        "bestEvaluatedBidder": best,
        "contractAmount": amount,
        "contractCurrency": currency_from_amount(amount),
        "bidders": bidders,
        "sourceMetadata": metadata,
        "lifecycleEvents": [{
            "stage": "evaluation",
            "title": "Best Evaluated Bidder notice published",
            "occurredAt": iso(display_date),
            "sourceUrl": url,
            "details": {
                "bestEvaluatedBidder": best,
                "contractAmount": amount,
            },
        }],
    }


def parse_contract_award_detail(html: str, url: str) -> dict | None:
    soup = BeautifulSoup(html, "html.parser")
    metadata = metadata_from_two_column_tables(soup)
    reference = metadata_value(metadata, "Procurement Reference Number", "Procurement Ref Number", "Reference Number")
    title = metadata_value(metadata, "Subject of Procurement", "Procurement Subject")
    organization = metadata_value(metadata, "Procurement Entity", "Procuring Entity")
    if not reference or not title:
        return None

    provider = metadata_value(metadata, "Provider", "Supplier", "Contractor", "Awarded To", "Successful Bidder")
    amount = metadata_value(metadata, "Contract Price", "Total Contract Price", "Award Amount")
    issued = parse_datetime(metadata_value(metadata, "Issued", "Date of Award", "Award Date", "Published on"))
    return {
        "referenceNumber": reference,
        "organization": organization,
        "title": title,
        "procurementMethod": metadata_value(metadata, "Method of Procurement", "Procurement Method"),
        "status": "awarded",
        "sourceStage": "Contract award",
        "bestEvaluatedBidder": provider,
        "contractAmount": amount,
        "contractCurrency": currency_from_amount(amount),
        "bidders": ([{
            "name": provider,
            "address": "",
            "submissionAt": "",
            "amount": amount,
            "currency": currency_from_amount(amount),
            "rank": "1",
            "status": "Awarded",
            "evaluationStage": "Contract award",
            "reasons": [],
        }] if provider else []),
        "sourceMetadata": metadata,
        "lifecycleEvents": [{
            "stage": "award",
            "title": "Contract awarded",
            "occurredAt": iso(issued),
            "sourceUrl": url,
            "details": {"provider": provider, "contractAmount": amount},
        }],
    }


def collect_lifecycle_records(fetch_url) -> list[dict]:
    """Collect public eGP BEB and contract-award lifecycle pages.

    The eGP list pages can legitimately be empty. We therefore return an empty
    list rather than fabricating lifecycle events. Individual report pages are
    only fetched when a public unauthenticated link is present in the list HTML.
    """
    records: list[dict] = []
    seen: set[tuple[str, str]] = set()

    sources = (
        (BEB_LIST_URL, ("/best-evaluated-bidder-notice-report/",), parse_beb_detail),
        (CONTRACTS_LIST_URL, ("/contract-award/", "/contracts-awarded/", "/contract-awarded/"), parse_contract_award_detail),
    )
    for list_url, tokens, parser in sources:
        try:
            listing = fetch_url(list_url)
        except Exception:
            continue
        for detail_url in _individual_links(listing, list_url, tokens):
            if detail_url.rstrip("/") == list_url.rstrip("/"):
                continue
            try:
                raw = fetch_url(detail_url)
                record = parser(raw, detail_url)
            except Exception:
                continue
            if not record:
                continue
            key = (clean(record.get("referenceNumber")).lower(), clean(record.get("sourceStage")).lower())
            if key in seen:
                continue
            seen.add(key)
            records.append(record)
    return records
