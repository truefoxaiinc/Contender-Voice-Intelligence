from datetime import datetime
from enum import Enum
from typing import Any, List, Optional
from pydantic import BaseModel, Field


class CallStatus(str, Enum):
    NEW = "New"
    IN_REVIEW = "In Review"
    CALLBACK_REQUIRED = "Callback Required"
    IN_PROGRESS = "In Progress"
    COMPLETED = "Completed"

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


class AnalyzeCallRequest(BaseModel):
    transcript: Optional[str] = Field(None, min_length=1)


class StatusUpdateRequest(BaseModel):
    status: CallStatus


class CallAnalysisUpdate(BaseModel):
    caller_name: Optional[str] = None
    caller_phone: Optional[str] = None
    company_name: Optional[str] = None
    category: str
    priority: str
    priority_reason: str
    summary: str
    important_information: List[str] = Field(default_factory=list)
    recommended_next_action: str
    missing_information: List[str] = Field(default_factory=list)
    confidence_notes: List[str] = Field(default_factory=list)
    transcript: str = ""


class CallEvent(BaseModel):
    id: int
    call_id: str
    event_type: str
    previous_value: Optional[str] = None
    new_value: Optional[str] = None
    timestamp: datetime


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: int
    name: str
    email: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class CallRecord(CallAnalysisResponse):
    id: str
    filename: str
    created_at: datetime
    transcript: str = ""
    status: CallStatus = CallStatus.NEW
    processing_status: str = "Uploaded"
    processing_error: Optional[str] = None
    transcript_segments: List[dict[str, Any]] = Field(default_factory=list)
