from __future__ import annotations

from datetime import datetime
from typing import Literal
from pydantic import BaseModel, HttpUrl


BidStatus = Literal["planned", "open", "closed", "evaluation", "awarded", "cancelled"]


class SourceRef(BaseModel):
    name: str
    url: HttpUrl
    detected_at: datetime


class NormalizedBid(BaseModel):
    title: str
    organization: str
    reference_number: str = ""
    description: str = ""
    category: str = ""
    procurement_type: str = ""
    published_at: datetime | None = None
    deadline_at: datetime | None = None
    deadline_precision: Literal["date", "datetime", "unknown"] = "unknown"
    status: BidStatus = "open"
    sources: list[SourceRef]

    def canonical_key(self) -> str:
        reference = "".join(self.reference_number.lower().split())
        if reference:
            return f"ref:{reference}"
        org = " ".join(self.organization.lower().split())
        title = " ".join(self.title.lower().split())
        return f"org-title:{org}|{title}"
