from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import CurrentUserDep, DbSessionDep, require_permission
from app.models.employee import Employee
from app.models.role import Permission, Role, EmployeeRole, EmployeePermission, RolePermission
from app.schemas.role import (
    EmployeePermissionAssignment,
    EmployeeRoleAssignment,
    PermissionResponse,
    RoleBriefResponse,
    RoleCreate,
    RoleResponse,
    RoleUpdate,
)

router = APIRouter(prefix="/roles", tags=["roles"])
perm_router = APIRouter(prefix="/permissions", tags=["permissions"])
emp_router = APIRouter(prefix="/employees", tags=["employees"])


# ── Permissions ──────────────────────────────────────────


@perm_router.get("/", response_model=list[PermissionResponse])
async def list_permissions(
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> list[Permission]:
    result = await db.execute(select(Permission).order_by(Permission.code))
    return list(result.scalars().all())


# ── Roles CRUD ────────────────────────────────────────────


@router.post("/", response_model=RoleResponse, status_code=status.HTTP_201_CREATED)
async def create_role(
    role_data: RoleCreate,
    db: DbSessionDep,
    _: None = Depends(require_permission("admin.roles")),
) -> Role:
    existing = await db.execute(select(Role).where(Role.name == role_data.name))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A role with this name already exists",
        )

    role = Role(
        name=role_data.name,
        description=role_data.description,
    )
    db.add(role)
    await db.flush()

    if role_data.permission_ids:
        result = await db.execute(
            select(Permission).where(Permission.id.in_(role_data.permission_ids))
        )
        perms = result.scalars().all()
        for perm in perms:
            rp = RolePermission(role_id=role.id, permission_id=perm.id)
            db.add(rp)

    await db.flush()
    await db.refresh(role)
    return await _load_role_with_permissions(db, role.id)


@router.get("/", response_model=list[RoleBriefResponse])
async def list_roles(
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> list[RoleBriefResponse]:
    result = await db.execute(
        select(Role).order_by(Role.name)
    )
    roles = result.scalars().all()
    output = []
    for role in roles:
        count_result = await db.execute(
            select(RolePermission).where(RolePermission.role_id == role.id)
        )
        output.append(RoleBriefResponse(
            id=role.id,
            name=role.name,
            description=role.description,
            permission_count=len(count_result.scalars().all()),
        ))
    return output


@router.get("/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: str,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> RoleResponse:
    return await _load_role_with_permissions(db, role_id)


@router.patch("/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: str,
    role_data: RoleUpdate,
    db: DbSessionDep,
    _: None = Depends(require_permission("admin.roles")),
) -> RoleResponse:
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    if role_data.name is not None:
        existing = await db.execute(
            select(Role).where(Role.name == role_data.name, Role.id != role_id)
        )
        if existing.scalar_one_or_none() is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A role with this name already exists",
            )
        role.name = role_data.name
    if role_data.description is not None:
        role.description = role_data.description

    if role_data.permission_ids is not None:
        result = await db.execute(
            select(RolePermission).where(RolePermission.role_id == role_id)
        )
        for rp in result.scalars().all():
            await db.delete(rp)

        if role_data.permission_ids:
            perm_result = await db.execute(
                select(Permission).where(Permission.id.in_(role_data.permission_ids))
            )
            for perm in perm_result.scalars().all():
                db.add(RolePermission(role_id=role.id, permission_id=perm.id))

    await db.flush()
    return await _load_role_with_permissions(db, role.id)


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: str,
    db: DbSessionDep,
    _: None = Depends(require_permission("admin.roles")),
) -> None:
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    if role.is_default:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot delete a default role",
        )

    await db.delete(role)
    await db.flush()


async def _load_role_with_permissions(db: AsyncSession, role_id: str) -> RoleResponse:
    result = await db.execute(
        select(Role)
        .options(selectinload(Role.permissions).selectinload(RolePermission.permission))
        .where(Role.id == role_id)
    )
    role = result.scalar_one_or_none()
    if role is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")

    return RoleResponse(
        id=role.id,
        name=role.name,
        description=role.description,
        is_default=role.is_default,
        permissions=[
            PermissionResponse.model_validate(rp.permission)
            for rp in role.permissions
        ],
    )


# ── Employee Role Assignment ─────────────────────────────


@emp_router.post("/{employee_id}/roles", response_model=list[RoleBriefResponse])
async def assign_employee_roles(
    employee_id: str,
    assignment: EmployeeRoleAssignment,
    db: DbSessionDep,
    _: None = Depends(require_permission("admin.roles")),
) -> list[RoleBriefResponse]:
    emp_result = await db.execute(select(Employee).where(Employee.id == employee_id))
    employee = emp_result.scalar_one_or_none()
    if employee is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

    result = await db.execute(
        select(EmployeeRole).where(EmployeeRole.employee_id == employee_id)
    )
    for er in result.scalars().all():
        await db.delete(er)

    for role_id in assignment.role_ids:
        role_result = await db.execute(select(Role).where(Role.id == role_id))
        if role_result.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Role {role_id} not found",
            )
        db.add(EmployeeRole(employee_id=employee_id, role_id=role_id))

    await db.flush()
    return await _get_employee_role_briefs(db, employee_id)


@emp_router.get("/{employee_id}/roles", response_model=list[RoleBriefResponse])
async def get_employee_roles(
    employee_id: str,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> list[RoleBriefResponse]:
    return await _get_employee_role_briefs(db, employee_id)


@emp_router.delete("/{employee_id}/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_employee_role(
    employee_id: str,
    role_id: str,
    db: DbSessionDep,
    _: None = Depends(require_permission("admin.roles")),
) -> None:
    result = await db.execute(
        select(EmployeeRole).where(
            EmployeeRole.employee_id == employee_id,
            EmployeeRole.role_id == role_id,
        )
    )
    er = result.scalar_one_or_none()
    if er is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    await db.delete(er)
    await db.flush()


async def _get_employee_role_briefs(db: AsyncSession, employee_id: str) -> list[RoleBriefResponse]:
    result = await db.execute(
        select(Role)
        .join(EmployeeRole, EmployeeRole.role_id == Role.id)
        .where(EmployeeRole.employee_id == employee_id)
        .order_by(Role.name)
    )
    roles = result.scalars().all()
    output = []
    for role in roles:
        count_result = await db.execute(
            select(RolePermission).where(RolePermission.role_id == role.id)
        )
        output.append(RoleBriefResponse(
            id=role.id,
            name=role.name,
            description=role.description,
            permission_count=len(count_result.scalars().all()),
        ))
    return output


# ── Employee Direct Permission Overrides ─────────────────


@emp_router.post("/{employee_id}/permissions", response_model=list[PermissionResponse])
async def add_employee_permission(
    employee_id: str,
    assignment: EmployeePermissionAssignment,
    db: DbSessionDep,
    _: None = Depends(require_permission("admin.permissions")),
) -> list[PermissionResponse]:
    emp_result = await db.execute(select(Employee).where(Employee.id == employee_id))
    if emp_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found")

    perm_result = await db.execute(
        select(Permission).where(Permission.id == assignment.permission_id)
    )
    perm = perm_result.scalar_one_or_none()
    if perm is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found")

    existing = await db.execute(
        select(EmployeePermission).where(
            EmployeePermission.employee_id == employee_id,
            EmployeePermission.permission_id == assignment.permission_id,
        )
    )
    if existing.scalar_one_or_none() is None:
        db.add(EmployeePermission(employee_id=employee_id, permission_id=perm.id))
        await db.flush()

    return await _get_employee_permissions(db, employee_id)


@emp_router.get("/{employee_id}/permissions", response_model=list[PermissionResponse])
async def get_employee_permissions(
    employee_id: str,
    db: DbSessionDep,
    current_user: CurrentUserDep,
) -> list[PermissionResponse]:
    return await _get_employee_permissions(db, employee_id)


@emp_router.delete(
    "/{employee_id}/permissions/{permission_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_employee_permission(
    employee_id: str,
    permission_id: str,
    db: DbSessionDep,
    _: None = Depends(require_permission("admin.permissions")),
) -> None:
    result = await db.execute(
        select(EmployeePermission).where(
            EmployeePermission.employee_id == employee_id,
            EmployeePermission.permission_id == permission_id,
        )
    )
    ep = result.scalar_one_or_none()
    if ep is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Override not found")
    await db.delete(ep)
    await db.flush()


async def _get_employee_permissions(db: AsyncSession, employee_id: str) -> list[PermissionResponse]:
    result = await db.execute(
        select(Permission)
        .join(EmployeePermission, EmployeePermission.permission_id == Permission.id)
        .where(EmployeePermission.employee_id == employee_id)
        .order_by(Permission.code)
    )
    return [PermissionResponse.model_validate(p) for p in result.scalars().all()]
