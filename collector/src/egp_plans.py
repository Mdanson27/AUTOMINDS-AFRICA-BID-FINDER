from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import hashlib
import re
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

from bs4 import BeautifulSoup
import httpx


KAMPALA = ZoneInfo("Africa/Kampala")


def clean(value: str) -> str:
    return re.sub(r"\s+", " ", value.replace("\xa0", " ")).strip()


@dataclass
class ProcurementPlanItem:
    number: int
    category: str
    estimated_amount_ugx: str


@dataclass
class ProcurementPlan:
    id: str
    name: str
    organization: str
    financial_year: str
    source_url: str
    excel_url: str = ""
    pdf_url: str = ""
    total_estimated_amount_ugx: str = ""
    items: list[ProcurementPlanItem] = field(default_factory=list)


class EGPProcurementPlansSource:
    name = "eGP Procurement Plans"
    source_id = "egp-procurement-plans"
    url = "https://egpuganda.go.ug/procurement-plans"

    def _fetch_url(self, url: str) -> str:
        response = httpx.get(
            url,
            timeout=45,
            follow_redirects=True,
            headers={
                "User-Agent": "AutoMindsBidFinder/1.0 (+public procurement indexing; Uganda)",
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        response.raise_for_status()
        return response.text

    def fetch(self) -> str:
        return self._fetch_url(self.url)

    @staticmethod
    def current_financial_year(now: datetime | None = None) -> str:
        local_now = (now or datetime.now(KAMPALA)).astimezone(KAMPALA)
        start_year = local_now.year if local_now.month >= 7 else local_now.year - 1
        start_year = max(start_year, 2026)
        return f"{start_year}-{start_year + 1}"

    def parse_index(self, raw: str, financial_year: str | None = None) -> list[ProcurementPlan]:
        target_year = financial_year or self.current_financial_year()
        soup = BeautifulSoup(raw, "html.parser")
        plans: list[ProcurementPlan] = []

        for table in soup.find_all("table"):
            headers = [clean(cell.get_text(" ", strip=True)).lower() for cell in table.find_all("th")]
            if not (
                any("plan name" in header for header in headers)
                and any("financial year" in header for header in headers)
            ):
                continue

            for row in table.find_all("tr"):
                cells = row.find_all("td")
                if len(cells) < 2:
                    continue
                name = clean(cells[0].get_text(" ", strip=True))
                year = clean(cells[1].get_text(" ", strip=True))
                if not name or year != target_year:
                    continue

                anchors = row.find_all("a", href=True)
                detail_anchor = next(
                    (
                        anchor
                        for anchor in anchors
                        if "view" in clean(anchor.get_text(" ", strip=True)).lower()
                        or "_plan_" in str(anchor.get("href", ""))
                    ),
                    anchors[0] if anchors else None,
                )
                excel_anchor = next(
                    (
                        anchor
                        for anchor in anchors
                        if "excel" in clean(anchor.get_text(" ", strip=True)).lower()
                        or ".xls" in str(anchor.get("href", "")).lower()
                    ),
                    None,
                )
                detail_url = urljoin(self.url, detail_anchor["href"]) if detail_anchor else self.url
                excel_url = urljoin(self.url, excel_anchor["href"]) if excel_anchor else ""
                stable = hashlib.sha256(f"{year}|{detail_url}|{name}".encode("utf-8")).hexdigest()[:24]
                plans.append(
                    ProcurementPlan(
                        id=stable,
                        name=name,
                        organization=name,
                        financial_year=year,
                        source_url=detail_url,
                        excel_url=excel_url,
                    )
                )

        unique: dict[str, ProcurementPlan] = {}
        for plan in plans:
            unique[plan.source_url] = plan
        return list(unique.values())

    def parse_detail(self, raw: str, plan: ProcurementPlan) -> ProcurementPlan:
        soup = BeautifulSoup(raw, "html.parser")

        title_node = soup.find(["h1", "h2"])
        title = clean(title_node.get_text(" ", strip=True)) if title_node else plan.name
        organization = re.sub(
            rf"\s+Procurement\s+Plan\s+for\s+{re.escape(plan.financial_year)}\s*$",
            "",
            title,
            flags=re.IGNORECASE,
        ).strip() or plan.organization

        pdf_url = plan.pdf_url
        excel_url = plan.excel_url
        for anchor in soup.find_all("a", href=True):
            text = clean(anchor.get_text(" ", strip=True)).lower()
            href = urljoin(plan.source_url, anchor["href"])
            lower_href = href.lower()
            if not pdf_url and ("download pdf" in text or lower_href.endswith(".pdf")):
                pdf_url = href
            if not excel_url and ("download excel" in text or lower_href.endswith((".xls", ".xlsx"))):
                excel_url = href

        items: list[ProcurementPlanItem] = []
        total = ""
        for table in soup.find_all("table"):
            headers = [clean(cell.get_text(" ", strip=True)).lower() for cell in table.find_all("th")]
            if not (
                any("group/category" in header or "category" == header for header in headers)
                and any("estimated amount" in header for header in headers)
            ):
                continue

            for row in table.find_all("tr"):
                cells = row.find_all("td")
                if len(cells) < 2:
                    continue
                values = [clean(cell.get_text(" ", strip=True)) for cell in cells]
                first = values[0].lower()
                if first == "total" or any(value.lower() == "total" for value in values[:2]):
                    amount_value = next((value for value in reversed(values) if re.search(r"\d", value)), "")
                    total = re.sub(r"^UGX:\s*", "", amount_value, flags=re.IGNORECASE).strip()
                    continue

                number = 0
                category = ""
                amount = ""
                if len(values) >= 3 and values[0].isdigit():
                    number = int(values[0])
                    category = values[1]
                    amount = values[2]
                elif len(values) >= 2:
                    category = values[-2]
                    amount = values[-1]

                if not category or not re.search(r"\d", amount):
                    continue
                if not number:
                    number = len(items) + 1
                items.append(
                    ProcurementPlanItem(
                        number=number,
                        category=category,
                        estimated_amount_ugx=re.sub(r"^UGX:\s*", "", amount, flags=re.IGNORECASE).strip(),
                    )
                )

        return ProcurementPlan(
            id=plan.id,
            name=title or plan.name,
            organization=organization,
            financial_year=plan.financial_year,
            source_url=plan.source_url,
            excel_url=excel_url,
            pdf_url=pdf_url,
            total_estimated_amount_ugx=total,
            items=items,
        )

    def collect(self, financial_year: str | None = None) -> list[ProcurementPlan]:
        raw = self.fetch()
        plans = self.parse_index(raw, financial_year=financial_year)
        enriched: list[ProcurementPlan] = []
        for plan in plans:
            try:
                detail_raw = self._fetch_url(plan.source_url)
                plan = self.parse_detail(detail_raw, plan)
            except Exception:
                pass
            enriched.append(plan)
        return enriched
