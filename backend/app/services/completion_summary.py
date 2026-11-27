"""竣工总结领域服务：汇总全部工序后编制竣工报告，前置校验全部工序已完成。

扩展：临时借阅凭据的授权结果落到竣工报告待办；编制人可在报告上消费凭据、
幂等引用并提交普通验收附件；撤回冲突后可按引用请求号查询裁决并判断能否
继续备案。借阅逻辑见 ``app.services.borrow_credential.BorrowFacade``。
"""
from __future__ import annotations

from typing import Any

from app.services.base import BaseModuleService
from app.services.borrow_credential import BorrowFacade, classify_op, engine
from app.store import store


class CompletionSummaryService(BorrowFacade, BaseModuleService):
    MODULE = "completion_summary"
    ENTITY = "竣工报告"
    OPERATION_TERM = "提交报告"
    LIST_FIELDS = ["修缮项目", "开工日期", "竣工日期", "实际工期", "质量评定", "编制人", "报告版本", "备注说明"]
    REQUIRED_FIELDS = ["修缮项目", "开工日期", "竣工日期"]
    STATUS_ORDER = ["编制中", "已提交", "已备案", "待补充"]
    ACTION_RULES = {
        "提交报告": "已提交",
        "执行备案": "已备案",
        "退回补充": "待补充",
        # 借阅凭据/附件相关动作由 run_action 分流
        "签发借阅凭据": "已签发",
        "签发凭据": "已签发",
        "引用附件": "已引用",
        "提交附件": "已引用",
        "撤回借阅授权": "已撤回",
        "继续备案": "已备案",
    }
    NEGATIVE_ACTIONS = []

    def cross_module_verify(
        self, entry_id: int, action: str, entry: dict[str, Any]
    ) -> tuple[bool, str]:
        if action == "提交报告":
            # 1. 所有工序必须完成
            incomplete = [
                r for r in store.rows("work_sequence") if r.get("status") != "已完成"
            ]
            if incomplete:
                names = [r.get("工序名称", "") for r in incomplete[:3]]
                return False, f"尚有{len(incomplete)}道工序未完成，如：{'、'.join(names)}"
            # 2. 所有材料必须签认
            unsigned_materials = [
                r for r in store.rows("material_verify") if r.get("status") not in ("已签认",)
            ]
            if unsigned_materials:
                return False, f"尚有{len(unsigned_materials)}组材料未签认"
            # 3. 所有验收必须签署
            unsigned_acceptance = [
                r for r in store.rows("acceptance_record") if r.get("status") != "已签署"
            ]
            if unsigned_acceptance:
                return False, f"尚有{len(unsigned_acceptance)}条验收未签署"
        if action == "执行备案":
            # 显式声明了必备附件时，必须有获准的引用覆盖
            required = entry.get("required_attachment_codes") or entry.get("必备附件")
            if required:
                from app.services.borrow_credential import REF_TABLE
                if isinstance(required, str):
                    required = [s.strip() for s in required.split(",") if s.strip()]
                approved_codes = {
                    str(r.get("attachment_code") or r.get("附件编号"))
                    for r in store.rows(REF_TABLE)
                    if r.get("granted") and str(r.get("report_id")) == str(entry_id)
                }
                missing = [code for code in required if str(code) not in approved_codes]
                if missing:
                    return False, f"必备验收附件尚无获准引用：{'、'.join(missing)}"
            # 备案前所有档案必须入库
            unarchived = [
                r for r in store.rows("archive_mgmt") if r.get("status") != "已入库"
            ]
            if unarchived and len(unarchived) > len(store.rows("archive_mgmt")) * 0.3:
                return False, f"尚有{len(unarchived)}份档案未入库"
        return True, ""

    def cross_module_effect(
        self, entry_id: int, action: str, entry: dict[str, Any]
    ) -> list[dict]:
        effects = []
        if action == "执行备案":
            # 备案后锁定所有关联记录
            for ws_row in store.rows("work_sequence"):
                ws_row["已备案锁定"] = True
                effects.append(dict(ws_row))
            for acc in store.rows("acceptance_record"):
                acc["已备案锁定"] = True
                effects.append(dict(acc))
            for log in store.rows("restoration_log"):
                log["已备案锁定"] = True
                effects.append(dict(log))
        return effects

    # ── 动作入口：报告 id 即路径资源 id，默认注入为 report ──
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

        # “执行备案”始终走原生备案流程（含档案入库率校验）
        if act == "执行备案":
            return super().run_action(entry_id, act)  # type: ignore[arg-type]

        op = classify_op(act)
        signal = op is not None or context_has_borrow_params(ctx) or borrowish_action_name(act)
        if signal:
            params = {k: v for k, v in ctx.items() if k != "action"}
            if entry_id is not None:
                params.setdefault("report", int(entry_id))
            if op is None:
                op = default_op_for_name(act)
            return engine.dispatch(op, **params)

        return super().run_action(entry_id, act)  # type: ignore[arg-type]


def __getattr__(name: str):
    from app.services.borrow_credential import module_getattr
    return module_getattr(name, primary_service=CompletionSummaryService, module_globals=globals())
