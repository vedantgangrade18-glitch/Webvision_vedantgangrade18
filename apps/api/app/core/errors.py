"""Error envelope: `{error: {code, message_key, details}}` (Part 2 §14)."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class AppError(Exception):
    def __init__(self, status: int, code: str, message_key: str | None = None, details: dict | None = None):
        super().__init__(code)
        self.status = status
        self.code = code
        self.message_key = message_key or f"errors.{code}"
        self.details = details or {}


def not_found(what: str = "resource") -> AppError:
    return AppError(404, "not_found", details={"resource": what})


def forbidden(code: str = "forbidden") -> AppError:
    return AppError(403, code)


def bad_request(code: str, **details) -> AppError:
    return AppError(400, code, details=details)


def conflict(code: str, **details) -> AppError:
    return AppError(409, code, details=details)


def _body(code: str, message_key: str, details: dict) -> dict:
    return {"error": {"code": code, "message_key": message_key, "details": details}}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError):
        return JSONResponse(_body(exc.code, exc.message_key, exc.details), status_code=exc.status)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        details = {"fields": [{"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]} for e in exc.errors()]}
        return JSONResponse(_body("validation_error", "errors.validation_error", details), status_code=422)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException):
        code = {401: "unauthorized", 403: "forbidden", 404: "not_found", 405: "method_not_allowed"}.get(
            exc.status_code, "http_error"
        )
        return JSONResponse(_body(code, f"errors.{code}", {}), status_code=exc.status_code)
