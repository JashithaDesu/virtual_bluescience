from pydantic import BaseModel
from typing import Literal, Optional
from datetime import datetime
from uuid import UUID

ClaimField = Literal["offering", "technology", "expertise", "application_area", "market",
                     "customer_group", "geography", "priority", "collaboration", "domain",
                     "relevant_topic", "size", "founded", "location"]

class ProfileClaim(BaseModel):
    id: UUID
    company_id: str
    field: ClaimField
    value: Optional[str] = None
    type: Literal["stated", "inferred", "missing"]
    quote: Optional[str] = None
    source_url: Optional[str] = None
    retrieved_at: Optional[datetime] = None
    confidence: Literal["high", "medium", "low"] = "medium"
    origin: Literal["agent", "user"] = "agent"
    verified: bool = False
    is_simulated: bool = False
