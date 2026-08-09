import uuid
from pydantic import BaseModel, EmailStr


# Shared properties across requests
class UserBase(BaseModel):
    email: EmailStr
    full_name: str | None = None


# Payload required when signing up
class UserCreate(UserBase):
    password: str


# Response payload sent to clients (never exposes hashed_password)
class UserResponse(UserBase):
    id: uuid.UUID
    is_verified: bool
    is_active: bool

    class Config:
        from_attributes = True  # Allows Pydantic to read directly from SQLAlchemy models


# JWT Auth schemas
class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str | None = None
    type: str | None = None