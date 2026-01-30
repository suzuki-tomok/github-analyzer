# app/schemas/response/common.py
from pydantic import BaseModel
from typing import Generic, TypeVar

T = TypeVar("T")


class SuccessResponse(BaseModel, Generic[T]):
    status: str = "success"
    data: T


class ErrorResponse(BaseModel):
    status: str = "error"
    code: str
    message: str