from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class PriorityEnum(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class TaskCreate(BaseModel):
    """Create a new task.

    OPENAPI IMPERFECTION: no field examples provided."""
    title: str = Field(min_length=1, max_length=200)
    description: Optional[str] = None
    completed: bool = False
    priority: PriorityEnum = PriorityEnum.medium


class TaskUpdate(BaseModel):
    """Update an existing task.

    OPENAPI IMPERFECTION: no field examples, no description on fields."""
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    completed: Optional[bool] = None
    priority: Optional[PriorityEnum] = None


class TaskResponse(BaseModel):
    """OPENAPI IMPERFECTION: documents 'description' as always present,
    but the runtime sometimes omits it (see inconsistency #4)."""
    id: int
    title: str = Field(description="The task title")
    description: Optional[str]
    # IMPERFECTION: 'completed' has no description
    completed: bool
    priority: str  # IMPERFECTION: documented as 'str', not as PriorityEnum
    owner_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class TaskResponseMinimal(BaseModel):
    """Minimal task view — intentionally incomplete schema.
    Used by endpoints that don't document all returned fields."""
    id: int
    title: str
    completed: bool
