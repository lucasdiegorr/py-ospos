import asyncio

from sqlalchemy import select

from app.core.security import get_password_hash
from app.db.session import async_session_maker
from app.models.employee import Employee
from app.models.role import EmployeeRole, Role


async def seed_admin() -> None:
    async with async_session_maker() as session:
        result = await session.execute(
            select(Employee).where(Employee.username == "admin")
        )
        admin = result.scalar_one_or_none()
        if admin is not None:
            print("Admin user already exists, skipping seed.")
            return

        admin = Employee(
            username="admin",
            password_hash=get_password_hash("admin"),
            first_name="Admin",
            last_name="User",
            email="admin@example.com",
            phone="+00000000000",
            is_active=True,
        )
        session.add(admin)
        await session.flush()

        role_result = await session.execute(
            select(Role).where(Role.name == "Admin")
        )
        admin_role = role_result.scalar_one_or_none()
        if admin_role is not None:
            er = EmployeeRole(employee_id=admin.id, role_id=admin_role.id)
            session.add(er)

        await session.commit()
        print("Admin user created (admin/admin) with Admin role.")


def main() -> None:
    asyncio.run(seed_admin())


if __name__ == "__main__":
    main()
