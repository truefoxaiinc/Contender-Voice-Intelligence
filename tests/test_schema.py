import pytest
from pydantic import ValidationError
from src.schemas import CallAnalysisResponse
from src.prompts import APPROVED_CATEGORIES


def test_valid_call_analysis_response():
    """Test that valid JSON data passes Pydantic validation successfully[cite: 1]."""
    data = {
        "caller_name": "John Doe",
        "caller_phone": "+1-555-0199",
        "company_name": "ABC Logistics",
        "category": "Shipment Tracking Inquiry",
        "priority": "High",
        "priority_reason": "Delivery expected today.",
        "summary": "Customer requested urgent shipment status.",
        "important_information": ["Shipment ID: 458"],
        "recommended_next_action": "Check shipment status and call back.",
        "missing_information": [],
        "confidence_notes": []
    }

    # Should instantiate without raising any validation error
    response = CallAnalysisResponse(**data)
    assert response.caller_name == "John Doe"
    assert response.category in APPROVED_CATEGORIES
    assert response.priority == "High"


def test_null_optional_fields():
    """Test that missing/null optional fields default gracefully[cite: 1]."""
    data = {
        "caller_name": None,
        "caller_phone": None,
        "company_name": None,
        "category": "General Inquiry",
        "priority": "Normal",
        "priority_reason": "Routine inquiry.",
        "summary": "Unidentified caller asked general questions.",
        "recommended_next_action": "No immediate callback required."
    }

    response = CallAnalysisResponse(**data)
    assert response.caller_name is None
    assert response.caller_phone is None
    assert response.important_information == []  # Defaults to empty list
    assert response.missing_information == []  # Defaults to empty list


def test_missing_required_field_raises_error():
    """Test that missing required fields (like priority or summary) throw a ValidationError[cite: 1]."""
    invalid_data = {
        "caller_name": "Jane Smith",
        "category": "Delivery Issue",
        # Missing required 'priority', 'priority_reason', 'summary', 'recommended_next_action'
    }

    with pytest.raises(ValidationError):
        CallAnalysisResponse(**invalid_data)