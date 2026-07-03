from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

from .models import SourceType, Status


class CamelModel(BaseModel):
    """Base model: accepts/serialises camelCase, populatable by field name too."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class StrictCamelModel(CamelModel):
    """Input model that rejects unknown fields (defense against field smuggling)."""

    model_config = ConfigDict(
        alias_generator=to_camel, populate_by_name=True, extra="forbid"
    )


# --------------------------------------------------------------------------- #
# Inputs
# --------------------------------------------------------------------------- #
class CreateApprovalRequestIn(StrictCamelModel):
    source_type: SourceType
    source_id: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=1, max_length=500)
    description: Optional[str] = Field(default=None, max_length=5000)
    reviewer_user_ids: List[str] = Field(default_factory=list, max_length=100)

    @field_validator("reviewer_user_ids")
    @classmethod
    def _reviewers_non_empty(cls, value: List[str]) -> List[str]:
        for item in value:
            if not item or not item.strip():
                raise ValueError("reviewerUserIds must not contain empty ids")
        return value


class ApproveIn(StrictCamelModel):
    comment: Optional[str] = Field(default=None, max_length=2000)


class RejectIn(StrictCamelModel):
    reason: str = Field(min_length=1, max_length=2000)


class CancelIn(StrictCamelModel):
    reason: str = Field(min_length=1, max_length=2000)


# --------------------------------------------------------------------------- #
# Outputs
# --------------------------------------------------------------------------- #
class DecisionOut(CamelModel):
    comment: Optional[str] = None
    reason: Optional[str] = None
    decided_by: Optional[str] = None
    decided_at: Optional[datetime] = None


class ApprovalRequestOut(CamelModel):
    id: str
    workspace_id: str
    source_type: SourceType
    source_id: str
    title: str
    description: Optional[str]
    reviewer_user_ids: List[str]
    status: Status
    decision: Optional[DecisionOut] = None
    created_by: str
    created_at: datetime
    updated_at: datetime


class ApprovalRequestListOut(CamelModel):
    items: List[ApprovalRequestOut]
    count: int
