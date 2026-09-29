"""User and token models."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    email: EmailStr
    # 72 bytes, not characters: that is bcrypt's hard input limit, and it
    # raises on anything longer rather than truncating.
    password: str = Field(min_length=8)
    name: str | None = None

    @field_validator("password")
    @classmethod
    def _within_bcrypt_limit(cls, value: str) -> str:
        if len(value.encode("utf-8")) > 72:
            raise ValueError("password must be at most 72 bytes")
        return value


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str
    name: str | None = None
    is_admin: bool
    storage_used_bytes: int


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
