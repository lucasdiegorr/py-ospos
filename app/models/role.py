from sqlalchemy import Boolean, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Role(BaseModel):
    __tablename__ = "roles"

    name: Mapped[str] = mapped_column(String(50), unique=True)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)

    permissions: Mapped[list["RolePermission"]] = relationship(
        "RolePermission", back_populates="role", cascade="all, delete-orphan"
    )


class Permission(BaseModel):
    __tablename__ = "permissions"

    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)


class RolePermission(BaseModel):
    __tablename__ = "role_permissions"

    role_id: Mapped[str] = mapped_column(String(36), ForeignKey("roles.id", ondelete="CASCADE"))
    permission_id: Mapped[str] = mapped_column(String(36), ForeignKey("permissions.id", ondelete="CASCADE"))

    role: Mapped[Role] = relationship("Role", back_populates="permissions")
    permission: Mapped[Permission] = relationship("Permission")


class EmployeeRole(BaseModel):
    __tablename__ = "employee_roles"

    employee_id: Mapped[str] = mapped_column(String(36), ForeignKey("employees.id", ondelete="CASCADE"))
    role_id: Mapped[str] = mapped_column(String(36), ForeignKey("roles.id", ondelete="CASCADE"))


class EmployeePermission(BaseModel):
    __tablename__ = "employee_permissions"

    employee_id: Mapped[str] = mapped_column(String(36), ForeignKey("employees.id", ondelete="CASCADE"))
    permission_id: Mapped[str] = mapped_column(String(36), ForeignKey("permissions.id", ondelete="CASCADE"))
