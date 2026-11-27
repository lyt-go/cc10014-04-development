"""模块名别名：完整实现见 app.services.borrow_credential。"""
from __future__ import annotations

from app.services.borrow_credential import *  # noqa: F401,F403
from app.services.borrow_credential import (  # noqa: F401
    ActionOutcome,
    BorrowCredentialService,
    BorrowEngine,
    BorrowFacade,
    BoolResult,
    classify_op,
    credential_service,
    engine,
    module_getattr,
    borrow_service,
)


def __getattr__(name: str):
    return module_getattr(
        name,
        primary_service=BorrowCredentialService,
        module_globals=globals(),
    )
