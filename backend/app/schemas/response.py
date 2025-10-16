"""
统一API响应格式Schema
"""
from typing import Generic, TypeVar, Optional, Any
from pydantic import Field, BaseModel


T = TypeVar('T')


class ApiResponse(BaseModel, Generic[T]):
    """统一API响应格式"""
    success: bool = Field(default=True, description="请求是否成功")
    data: Optional[T] = Field(None, description="响应数据")
    message: Optional[str] = Field(None, description="响应消息")
    error: Optional[str] = Field(None, description="错误信息")
    code: int = Field(default=200, description="响应代码")

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {"id": "123", "name": "Example"},
                "message": "操作成功",
                "code": 200
            }
        }


class PaginationMeta(BaseModel):
    """分页元数据"""
    page: int = Field(..., description="当前页码")
    limit: int = Field(..., description="每页数量")
    total: int = Field(..., description="总记录数")
    total_pages: int = Field(..., description="总页数")


class PaginatedResponse(BaseModel, Generic[T]):
    """分页响应格式"""
    success: bool = Field(default=True, description="请求是否成功")
    items: list[T] = Field(..., description="数据列表")
    pagination: PaginationMeta = Field(..., description="分页信息")
    message: Optional[str] = Field(None, description="响应消息")
    code: int = Field(default=200, description="响应代码")


class ErrorResponse(BaseModel):
    """错误响应格式"""
    success: bool = Field(default=False, description="请求失败")
    error: str = Field(..., description="错误信息")
    detail: Optional[Any] = Field(None, description="错误详情")
    code: int = Field(..., description="错误代码")

    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error": "资源不存在",
                "detail": "数据源ID不存在",
                "code": 404
            }
        }


def success_response(
    data: Any = None,
    message: str = "操作成功",
    code: int = 200
) -> dict:
    """创建成功响应"""
    return {
        "success": True,
        "data": data,
        "message": message,
        "code": code
    }


def error_response(
    error: str,
    detail: Any = None,
    code: int = 400
) -> dict:
    """创建错误响应"""
    return {
        "success": False,
        "error": error,
        "detail": detail,
        "code": code
    }


def paginated_response(
    items: list,
    page: int,
    limit: int,
    total: int,
    message: str = None
) -> dict:
    """创建分页响应"""
    total_pages = (total + limit - 1) // limit  # 向上取整
    return {
        "success": True,
        "items": items,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": total_pages
        },
        "message": message,
        "code": 200
    }


__all__ = [
    "ApiResponse",
    "PaginationMeta",
    "PaginatedResponse",
    "ErrorResponse",
    "success_response",
    "error_response",
    "paginated_response",
]
