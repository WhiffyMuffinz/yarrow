"""User, token and email verification models."""

from typing import Annotated
from uuid import UUID

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
)


def normalize_email(value: str) -> str:
    """The one canonical form an email is stored and looked up in.

    EmailStr lowercases only the domain, so "Alice@Example.com" and
    "alice@example.com" would otherwise be two accounts, and a user who
    registered with one could not sign in with the other.
    """
    return value.strip().lower()


# Use for every email that arrives in a request body.
NormalizedEmail = Annotated[EmailStr, AfterValidator(normalize_email)]


class UserCreate(BaseModel):
    email: NormalizedEmail
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


class VerifyEmailRequest(BaseModel):
    email: NormalizedEmail
    code: str = Field(min_length=6, max_length=6, pattern=r"^[0-9]{6}$")


class ResendVerificationRequest(BaseModel):
    email: NormalizedEmail


class MessageResponse(BaseModel):
    message: str
