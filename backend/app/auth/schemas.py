"""Auth request/response schemas. Passwords are never returned."""
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=256)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: str
    name: str
    email: str
    role: str
    status: str
    id_number: str | None = None


class RegisterRequest(BaseModel):
    """Self-registration. Role is never accepted from the client: every
    account is created as `user` (least privilege) and any role/status key
    sent in the body is ignored, not honoured. Passwords require a minimum
    length only here, where they are set — login keeps accepting whatever
    existing accounts hold."""

    name: str = Field(min_length=1, max_length=200)
    id_number: str = Field(min_length=1, max_length=64)
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=256)


class RegisterResponse(BaseModel):
    id: str
    name: str
    id_number: str | None = None
    email: str
    role: str
    status: str
    created_at: str
