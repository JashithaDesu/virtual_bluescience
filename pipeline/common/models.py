from pydantic import BaseModel, HttpUrl
from typing import Literal, Optional
from datetime import datetime

Field = Literal["offering", "technology", "expertise", "application_area",
                "market", "customer_group", "geography", "priority",
                "collaboration", "domain", "relevant_topic"]

class ProfileClaim(BaseModel):
    company_id: str
    field: Field
    value: str
    type: Literal["stated", "inferred", "missing"]
    quote: Optional[str] = None        # required when type == "stated", < 25 words
    source_url: Optional[HttpUrl] = None
    retrieved_at: Optional[datetime] = None
    confidence: Literal["high", "medium", "low"] = "medium"
    origin: Literal["agent", "user"] = "agent"
    verified: bool = False             # set by the Validator
    is_simulated: bool = False
