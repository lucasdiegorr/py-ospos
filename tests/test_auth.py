import pytest
from httpx import AsyncClient

from app.core.security import create_refresh_token


@pytest.mark.anyio
async def test_login(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/employees/",
        json={
            "username": "loginuser",
            "password": "testpassword123",
            "first_name": "Login",
            "last_name": "User",
        },
    )

    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "loginuser", "password": "testpassword123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["employee"]["username"] == "loginuser"


@pytest.mark.anyio
async def test_login_json(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/employees/",
        json={
            "username": "jsonuser",
            "password": "testpassword123",
            "first_name": "Json",
            "last_name": "User",
        },
    )

    response = await client.post(
        "/api/v1/auth/login/json",
        json={"username": "jsonuser", "password": "testpassword123"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["employee"]["username"] == "jsonuser"


@pytest.mark.anyio
async def test_login_invalid(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        data={"username": "nobody", "password": "wrong"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect username or password"


@pytest.mark.anyio
async def test_refresh_token(client: AsyncClient) -> None:
    refresh_token = create_refresh_token(subject="test-user-id")

    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.anyio
async def test_refresh_token_invalid(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "invalid-token"},
    )
    assert response.status_code == 401
