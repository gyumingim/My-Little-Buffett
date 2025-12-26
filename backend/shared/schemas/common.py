from pydantic import BaseModel
from typing import Any, Generic, TypeVar

T = TypeVar("T")


class BaseResponse(BaseModel, Generic[T]):
    """기본 응답 스키마"""

    success: bool
    message: str
    data: T | None = None


class ErrorResponse(BaseModel):
    """에러 응답 스키마"""

    success: bool = False
    message: str
    error_code: str | None = None


class CompanyInfo(BaseModel):
    """기업 기본 정보"""

    corp_code: str
    corp_name: str
    stock_code: str | None = None
    corp_cls: str | None = None  # Y: 유가, K: 코스닥, N: 코넥스, E: 기타
