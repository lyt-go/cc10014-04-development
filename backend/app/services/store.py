"""兼容路径：部分调用方可能从 app.services.store 取内存仓库。"""
from __future__ import annotations

from app.store import Store, store

__all__ = ["Store", "store"]
