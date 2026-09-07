from __future__ import annotations

from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field, HttpUrl


BidStatus = Literal["planned", "open", "closed", "evaluation", "awarded", "cancelled"]


class SourceRef(BaseModel):
    name: str
    url: HttpUrl
    detected_at: datetime


class SourceDocument(BaseModel):
    title: str
    url: HttpUrl
    kind: str = ""


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

    # Rich source detail fields. These are intentionally generic so the same
    # structure can later be populated by newspapers, development partners and
    # direct organization websites without redesigning the core model.
    notice_type: str = ""
    opening_at: datetime | None = None
    application_url: HttpUrl | None = None
    source_metadata: dict[str, str] = Field(default_factory=dict)
    documents: list[SourceDocument] = Field(default_factory=list)

    def canonical_key(self) -> str:
        reference = "".join(self.reference_number.lower().split())
        if reference:
            return f"ref:{reference}"
        org = " ".join(self.organization.lower().split())
        title = " ".join(self.title.lower().split())
        return f"org-title:{org}|{title}"
