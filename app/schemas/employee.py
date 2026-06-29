from typing import Annotated

from pydantic import BaseModel, EmailStr, Field


class EmployeeBase(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    first_name: str = Field(min_length=1, max_length=50)
    last_name: str = Field(min_length=1, max_length=50)
    email: EmailStr | None = None
    phone: str | None = None


class EmployeeCreate(EmployeeBase):
    password: str = Field(min_length=8)


class EmployeeUpdate(BaseModel):
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None


class EmployeeResponse(EmployeeBase):
    id: str
    is_active: bool

    model_config = {"from_attributes": True}


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    token_type: str = "bearer"
    employee: EmployeeResponse