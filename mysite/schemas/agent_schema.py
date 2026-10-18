from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserRegisterSchema(BaseModel):
    full_name: str = Field(min_length=1, max_length=100)
    email: EmailStr = Field(max_length=254)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("full_name", mode="before")
    @classmethod
    def strip_name(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.lower()

    @field_validator("password")
    @classmethod
    def reject_blank_password(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Password must not be blank")
        return value


class UserResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: EmailStr
    created_at: datetime


class TokenSchema(BaseModel):
    access_token: str
    token_type: str = "bearer"
