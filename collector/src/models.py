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
    procurement_method: str = ""
    source_stage: str = ""
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

    @staticmethod
    def _identity_text(value: str) -> str:
        return " ".join(str(value or "").lower().split())

    def canonical_key(self) -> str:
        """Return a stable multi-field procurement identity.

        Reference numbers remain the strongest identifier, but are never used
        alone because public procurement sources can repeat or conflict on a
        reference. Organization is therefore part of every referenced identity.
        When a reference is unavailable we fall back to organization + title +
        canonical source, rather than title alone.
        """
        reference = "".join(self.reference_number.lower().split())
        organization = self._identity_text(self.organization)
        if reference:
            return f"ref-org:{reference}|{organization}"

        title = self._identity_text(self.title)
        source = self._identity_text(self.sources[0].name if self.sources else "")
        return f"org-title-source:{organization}|{title}|{source}"
