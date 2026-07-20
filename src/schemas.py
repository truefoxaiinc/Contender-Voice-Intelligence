from typing import List, Optional
from pydantic import BaseModel, Field

class CallAnalysisResponse(BaseModel):
    caller_name: Optional[str] = Field(None, description="Caller name or null")
    caller_phone: Optional[str] = Field(None, description="Caller phone or null")
    company_name: Optional[str] = Field(None, description="Company name or null")
    category: str = Field(..., description="Approved category")
    priority: str = Field(..., description="Urgent, High, Normal, Low")
    priority_reason: str = Field(..., description="Reason for priority assignment")
    summary: str = Field(..., description="Concise call summary")
    important_information: List[str] = Field(default_factory=list)
    recommended_next_action: str = Field(..., description="Recommended staff action")
    missing_information: List[str] = Field(default_factory=list)
    confidence_notes: List[str] = Field(default_factory=list)