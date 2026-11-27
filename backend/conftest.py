"""后端级 pytest 夹具：每个用例前后清空临时借阅凭据领域状态。

放在 backend 根目录，对 tests/ 下及根目录的用例都生效；与用例自带的
SEED_ROWS 重置夹具叠加也安全（两者都只做清空）。
"""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _reset_borrow_runtime():
    try:
        from app.services.borrow_credential import reset_runtime_state
        reset_runtime_state()
    except Exception:
        pass
    yield
    try:
        from app.services.borrow_credential import reset_runtime_state
        reset_runtime_state()
    except Exception:
        pass
