from datetime import datetime
from typing import Literal
from pydantic import BaseModel, HttpUrl

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
    status: Literal["planned", "open", "closed", "evaluation", "awarded", "cancelled"] = "open"
    sources: list[SourceRef]
