"""Global FastAPI exception handlers."""

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.exceptions import FridayException
from app.core.logging import logger
from app.domain.schemas import APIResponse, ErrorDetail


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(FridayException)
    async def friday_exception_handler(request: Request, exc: FridayException):
        logger.warning(f"Handled application exception: [{exc.code}] {exc.message}")
        return JSONResponse(
            status_code=exc.status_code,
            content=APIResponse(
                success=False,
                error=ErrorDetail(
                    code=exc.code,
                    message=exc.message,
                    details=exc.details,
                ),
            ).model_dump(),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.warning(f"Request validation error: {exc.errors()}")
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=APIResponse(
                success=False,
                error=ErrorDetail(
                    code="VALIDATION_ERROR",
                    message="Request payload failed schema validation.",
                    details={"errors": exc.errors()},
                ),
            ).model_dump(),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled server error: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=APIResponse(
                success=False,
                error=ErrorDetail(
                    code="INTERNAL_SERVER_ERROR",
                    message="An unexpected internal error occurred.",
                ),
            ).model_dump(),
        )
