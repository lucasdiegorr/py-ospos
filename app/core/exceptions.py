from typing import Annotated

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError


class NotFoundError(HTTPException):
    def __init__(self, detail: str = "Resource not found") -> None:
        super().__init__(status_code=404, detail=detail)


class ForbiddenError(HTTPException):
    def __init__(self, detail: str = "Not authorized") -> None:
        super().__init__(status_code=403, detail=detail)


class ConflictError(HTTPException):
    def __init__(self, detail: str = "Resource already exists") -> None:
        super().__init__(status_code=409, detail=detail)


async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={"detail": "A resource with this identifier already exists"},
    )


exception_handlers: dict[type[Exception], type] = {
    IntegrityError: integrity_error_handler,
}
