from __future__ import annotations

from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field, HttpUrl


BidStatus = Literal["planned", "open", "closed", "evaluation", "awarded", "cancelled"]
LifecycleStage = Literal[
    "advertised",
    "updated",
    "closed",
    "bid-opening",
    "evaluation",
    "award",
    "cancelled",
]


class SourceRef(BaseModel):
    name: str
    url: HttpUrl
    detected_at: datetime


class SourceDocument(BaseModel):
    title: str
    url: HttpUrl
    kind: str = ""


class ContactPoint(BaseModel):
    label: str = ""
    value: str
    kind: Literal["email", "phone", "address", "other"] = "other"


class BidderRecord(BaseModel):
    name: str
    address: str = ""
    submission_at: datetime | None = None
    amount: str = ""
    currency: str = ""
    rank: str = ""
    status: str = ""
    evaluation_stage: str = ""
    reasons: list[str] = Field(default_factory=list)


class OpeningParticipant(BaseModel):
    name: str
    address: str = ""
    position: str = ""
    department_company: str = ""


class AmendmentRecord(BaseModel):
    title: str
    url: HttpUrl | None = None
    published_at: datetime | None = None
    summary: str = ""


class LifecycleEvent(BaseModel):
    stage: LifecycleStage
    title: str
    occurred_at: datetime | None = None
    source_url: HttpUrl | None = None
    details: dict[str, str] = Field(default_factory=dict)


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

    # Rich source detail fields. These remain generic enough for sources other
    # than eGP, but Phase 4 uses them to preserve structured procurement facts
    # instead of flattening everything into description/sourceMetadata.
    notice_type: str = ""
    opening_at: datetime | None = None
    application_url: HttpUrl | None = None
    source_metadata: dict[str, str] = Field(default_factory=dict)
    documents: list[SourceDocument] = Field(default_factory=list)
    eligibility: list[str] = Field(default_factory=list)
    mandatory_requirements: list[str] = Field(default_factory=list)
    bid_security: str = ""
    tender_fee: str = ""
    submission_method: str = ""
    contacts: list[ContactPoint] = Field(default_factory=list)
    bidders: list[BidderRecord] = Field(default_factory=list)
    bids_received: int | None = None
    opening_participants: list[OpeningParticipant] = Field(default_factory=list)
    opening_committee: list[str] = Field(default_factory=list)
    amendments: list[AmendmentRecord] = Field(default_factory=list)
    lifecycle_events: list[LifecycleEvent] = Field(default_factory=list)
    best_evaluated_bidder: str = ""
    contract_amount: str = ""
    contract_currency: str = ""

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
