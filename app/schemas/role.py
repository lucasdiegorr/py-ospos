from pydantic import BaseModel, Field


class PermissionResponse(BaseModel):
    id: str
    code: str
    name: str
    description: str | None = None

    model_config = {"from_attributes": True}


class RoleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    description: str | None = Field(None, max_length=255)
    permission_ids: list[str] = []


class RoleUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=50)
    description: str | None = Field(None, max_length=255)
    permission_ids: list[str] | None = None


class RoleResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    is_default: bool = False
    permissions: list[PermissionResponse] = []

    model_config = {"from_attributes": True}


class RoleBriefResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    permission_count: int = 0

    model_config = {"from_attributes": True}


class EmployeeRoleAssignment(BaseModel):
    role_ids: list[str]


class EmployeePermissionAssignment(BaseModel):
    permission_id: str
