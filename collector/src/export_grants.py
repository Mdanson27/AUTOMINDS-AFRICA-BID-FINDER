from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "public" / "data"
GRANTS_API = "https://api.grants.gov/v1/api/search2"
KEYWORDS = ("Uganda", "East Africa", "Africa")


def stable_id(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:28]


def clean(value) -> str:
    return " ".join(str(value or "").replace("\xa0", " ").split()).strip()


def collect_grants() -> list[dict]:
    collected_at = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    found: dict[str, dict] = {}

    with httpx.Client(timeout=30.0, follow_redirects=True, headers={"User-Agent": "AutoMinds-Africa-Bid-Finder/1.0"}) as client:
        for keyword in KEYWORDS:
            response = client.post(
                GRANTS_API,
                json={
                    "rows": 100,
                    "keyword": keyword,
                    "oppStatuses": "posted|forecasted",
                    "fundingInstruments": "G|CA",
                },
            )
            response.raise_for_status()
            payload = response.json()
            data = payload.get("data") or {}
            for hit in data.get("oppHits") or []:
                title = clean(hit.get("title"))
                agency = clean(hit.get("agencyName") or hit.get("agencyCode"))
                number = clean(hit.get("number"))
                opportunity_id = clean(hit.get("id"))
                if not title or not opportunity_id:
                    continue

                searchable = f"{title} {agency}".lower()
                if not any(term in searchable for term in ("uganda", "africa", "african", "east africa")):
                    continue

                status_raw = clean(hit.get("oppStatus")).lower()
                status = "forecasted" if status_raw == "forecasted" else "open"
                source_url = f"https://www.grants.gov/search-results-detail/{opportunity_id}"
                found[opportunity_id] = {
                    "id": stable_id(f"grants-gov:{opportunity_id}"),
                    "title": title,
                    "funder": agency,
                    "opportunityNumber": number,
                    "summary": "",
                    "geography": "Uganda / Africa relevance detected from the public opportunity listing",
                    "fundingAmount": "",
                    "eligibility": "",
                    "openDate": clean(hit.get("openDate")),
                    "deadlineAt": clean(hit.get("closeDate")),
                    "status": status,
                    "sourceName": "Grants.gov",
                    "sourceUrl": source_url,
                    "applicationUrl": source_url,
                    "collectedAt": collected_at,
                }

    return sorted(found.values(), key=lambda item: (item.get("deadlineAt") or "9999", item["title"]))


def main() -> int:
    grants = collect_grants()
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    target = DATA_DIR / "grants.json"
    target.write_text(json.dumps(grants, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Exported {len(grants)} real grant opportunities to {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
