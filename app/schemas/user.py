from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserRegister(BaseModel):
    """Register a new user.

    OPENAPI IMPERFECTION: has examples on some fields but not others."""
    username: str = Field(
        min_length=3, max_length=50,
        json_schema_extra={"examples": ["alice"]},
    )
    email: EmailStr  # IMPERFECTION: no example, no description
    password: str = Field(
        min_length=6, max_length=128,
        description="User password",
        # IMPERFECTION: no example (sensitive field, but real APIs often omit)
    )


class UserLogin(BaseModel):
    # IMPERFECTION: no field descriptions, no examples at all
    username: str
    password: str


class UserResponse(BaseModel):
    """OPENAPI IMPERFECTION: documents 4 fields but the runtime
    User model also has 'updated_at' which is never exposed here."""
    id: int
    username: str
    email: str
    created_at: datetime
    # IMPERFECTION: updated_at exists on the model but is not in this schema

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str  # IMPERFECTION: no description, no example
    token_type: str = "bearer"
