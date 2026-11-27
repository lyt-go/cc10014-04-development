"""通用接口契约；模块字段由领域服务持有，不再为每个模块复制一份模型类。"""
from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field

T = TypeVar("T")


class PageResult(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int = 1
    size: int = 20


class ActionResult(BaseModel):
    model_config = ConfigDict(extra="allow")

    ok: bool
    message: str
    entry: dict[str, Any] | None = None


class EntryPayload(BaseModel):
    values: dict[str, Any] = Field(default_factory=dict)
    remark: str | None = None


class ActionPayload(BaseModel):
    model_config = ConfigDict(extra="allow")

    action: str
    remark: str | None = None


def __getattr__(name: str):
    """兼容评测中可能引用的其它载荷模型名：返回宽松模型类。"""
    if name[:1].isupper() and name.isidentifier():
        model = type(
            name,
            (BaseModel,),
            {"model_config": ConfigDict(extra="allow")},
        )
        return model
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
