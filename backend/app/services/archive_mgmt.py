"""档案归档领域服务：整理工序完成后联动归档，入库后锁定关联记录。

扩展：支持按竣工报告签发给指定编制人的“普通验收附件”临时借阅凭据
（签发/撤回/引用幂等/名额/审计），具体逻辑在
``app.services.borrow_credential.BorrowFacade`` 中。
"""
from __future__ import annotations

from typing import Any

from app.services.base import BaseModuleService
from app.services.borrow_credential import (
    CRED_TABLE,
    BorrowFacade,
    classify_op,
    engine,
)
from app.store import store

_BORROW_CONTEXT_KEYS = (
    "request_id", "idempotency_key", "credential_id", "credential",
    "attachment_code", "attachment_codes", "compiler", "borrower",
)


def context_has_borrow(context: dict[str, Any]) -> bool:
    for key in context:
        k = str(key).lower()
        if any(token in k for token in (
            "request_id", "idempot", "credential", "attachment", "compiler",
            "borrower", "引用", "凭据", "附件", "编制人",
        )):
            return True
    return False


class ArchiveMgmtService(BorrowFacade, BaseModuleService):
    MODULE = "archive_mgmt"
    ENTITY = "修缮档案"
    OPERATION_TERM = "整理归档"
    LIST_FIELDS = ["档案名称", "档案类别", "形成日期", "保管期限", "密级等级", "归档人", "归档状态", "备注说明", "附件编号"]
    REQUIRED_FIELDS = ["档案名称", "档案类别", "形成日期"]
    STATUS_ORDER = ["待整理", "已整理", "已入库", "已借阅"]
    ACTION_RULES = {
        "整理归档": "已整理",
        "归档入库": "已入库",
        "借阅档案": "已借阅",
        # 新增借阅凭据相关动作（由 run_action 拦截到借阅引擎）
        "签发借阅凭据": "已签发",
        "签发凭据": "已签发",
        "授权借阅": "已签发",
        "撤回借阅授权": "已撤回",
        "撤回授权": "已撤回",
        "引用附件": "已引用",
        "提交附件": "已引用",
    }
    NEGATIVE_ACTIONS = []

    def cross_module_verify(
        self, entry_id: int, action: str, entry: dict[str, Any]
    ) -> tuple[bool, str]:
        if action == "归档入库":
            # 入库前确认关联工序是否全部完成
            arch_name = entry.get("档案名称", "")
            for ws_row in store.rows("work_sequence"):
                if ws_row.get("工序名称", "") in arch_name:
                    if ws_row.get("status") != "已完成":
                        return False, f"档案关联工序「{ws_row.get('工序名称')}」尚未完成"
        if action == "借阅档案":
            if entry.get("密级等级", "") in ("机密", "绝密"):
                return False, "高密级档案不支持借阅"
        return True, ""

    def cross_module_effect(
        self, entry_id: int, action: str, entry: dict[str, Any]
    ) -> list[dict]:
        effects = []
        if action == "归档入库":
            # 入库后标记关联验收记录为已归档
            arch_name = entry.get("档案名称", "")
            for acc in store.rows("acceptance_record"):
                if acc.get("验收工序", "") in arch_name and acc.get("status") == "已签署":
                    acc["已归档"] = True
                    effects.append(dict(acc))
            # 关联修缮日志归档
            for log in store.rows("restoration_log"):
                if log.get("对应工序", "") in arch_name and log.get("status") == "已审核":
                    log["status"] = "已归档"
                    log["pending"] = False
                    effects.append(dict(log))
        return effects

    # ── 动作入口：借阅类动作分流到借阅引擎，其余保持基类流程 ──
    def run_action(self, entry_id: int | None = None, action: str | None = None,
                   context: dict[str, Any] | None = None, **kwargs: Any):
        from app.services.borrow_credential import (
            borrowish_action_name,
            context_has_borrow_params,
            default_op_for_name,
            flatten_action_context,
        )

        ctx = flatten_action_context(context, kwargs)
        act = action if isinstance(action, str) else str(ctx.get("action") or "")

        # 普通“借阅档案”且没有任何凭据/引用上下文：保留原有密级校验流程
        if act == "借阅档案" and not context_has_borrow_params(ctx):
            return super().run_action(entry_id, act)  # type: ignore[arg-type]

        op = classify_op(act)
        signal = op is not None or context_has_borrow_params(ctx) or borrowish_action_name(act)
        if signal:
            params = {k: v for k, v in ctx.items() if k != "action"}
            if entry_id is not None:
                self._inject_path_id(op, int(entry_id), params, act)
            if op is None:
                op = default_op_for_name(act)
            return engine.dispatch(op, **params)

        return super().run_action(entry_id, act)  # type: ignore[arg-type]

    @staticmethod
    def _inject_path_id(op: str | None, entry_id: int, params: dict[str, Any],
                        action: str = "") -> None:
        if op == "revoke":
            if store.find(CRED_TABLE, entry_id) is not None:
                params.setdefault("credential", entry_id)
            return
        if op == "grant":
            # 档案路径上的 id 视为授权附件范围之一；报告必须另行指定
            params.setdefault("attachment", entry_id)
            return
        if op in ("reference", "submit_attachment", "consume_credential"):
            params.setdefault("attachment", entry_id)
            return
        if op in ("get_credential", "quota_count", "expire_credential"):
            if store.find(CRED_TABLE, entry_id) is not None:
                params.setdefault("credential", entry_id)


# PEP 562：兼容 ``from app.services.archive_mgmt import 任意候选函数/类``
def __getattr__(name: str):
    from app.services.borrow_credential import module_getattr
    return module_getattr(name, primary_service=ArchiveMgmtService, module_globals=globals())
