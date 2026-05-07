from datetime import datetime

from pydantic import BaseModel, Field


class CommentCreate(BaseModel):
    """OPENAPI IMPERFECTION: has example but content max_length
    is documented as 2000 while the runtime actually accepts longer."""
    content: str = Field(
        min_length=1,
        max_length=2000,
        description="Comment body text",
        json_schema_extra={"examples": ["This looks great, shipping it!"]},
    )


class CommentResponse(BaseModel):
    """OPENAPI IMPERFECTION: missing descriptions on most fields."""
    id: int
    content: str
    task_id: int  # IMPERFECTION: no description — what does this reference?
    author_id: int  # IMPERFECTION: no description — who is the author?
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
