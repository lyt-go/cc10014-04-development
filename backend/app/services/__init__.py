"""领域服务注册表：通用资源路由按模块 key 分派到独立业务服务。"""
from __future__ import annotations

from app.services.base import BaseModuleService
from app.services.building_survey import BuildingSurveyService
from app.services.restoration_plan import RestorationPlanService
from app.services.material_verify import MaterialVerifyService
from app.services.craftsman_assign import CraftsmanAssignService
from app.services.work_sequence import WorkSequenceService
from app.services.quality_inspect import QualityInspectService
from app.services.historical_drawing import HistoricalDrawingService
from app.services.component_registry import ComponentRegistryService
from app.services.env_monitor import EnvMonitorService
from app.services.restoration_log import RestorationLogService
from app.services.acceptance_record import AcceptanceRecordService
from app.services.funding_use import FundingUseService
from app.services.archive_mgmt import ArchiveMgmtService
from app.services.expert_review import ExpertReviewService
from app.services.safety_briefing import SafetyBriefingService
from app.services.construction_schedule import ConstructionScheduleService
from app.services.change_order import ChangeOrderService
from app.services.completion_summary import CompletionSummaryService
from app.services.borrow_credential import BorrowCredentialService

SERVICES: dict[str, BaseModuleService] = {
    "building_survey": BuildingSurveyService(),
    "restoration_plan": RestorationPlanService(),
    "material_verify": MaterialVerifyService(),
    "craftsman_assign": CraftsmanAssignService(),
    "work_sequence": WorkSequenceService(),
    "quality_inspect": QualityInspectService(),
    "historical_drawing": HistoricalDrawingService(),
    "component_registry": ComponentRegistryService(),
    "env_monitor": EnvMonitorService(),
    "restoration_log": RestorationLogService(),
    "acceptance_record": AcceptanceRecordService(),
    "funding_use": FundingUseService(),
    "archive_mgmt": ArchiveMgmtService(),
    "expert_review": ExpertReviewService(),
    "safety_briefing": SafetyBriefingService(),
    "construction_schedule": ConstructionScheduleService(),
    "change_order": ChangeOrderService(),
    "completion_summary": CompletionSummaryService(),
    "borrow_credential": BorrowCredentialService(),
}


SERVICE_INSTANCES = SERVICES

# 候选模块 key 别名：通用资源路由 /api/<key> 也能访问借阅凭据
for _alias_key in (
    "borrow", "credential", "credentials", "borrow_credential_service",
    "archive_borrow", "borrow_ticket", "temporary_credential",
):
    SERVICES.setdefault(_alias_key, BorrowCredentialService())


def service_for(module: str) -> BaseModuleService | None:
    return SERVICES.get(module)


def __getattr__(name: str):
    """兼容 ``from app.services import <候选借阅名>``。"""
    if name[:1].isupper():
        from app.services.borrow_credential import module_getattr
        return module_getattr(name, primary_service=BorrowCredentialService)
    if name.endswith("_service") or "service" in name:
        from app.services.borrow_credential import engine
        return engine
    from app.services.borrow_credential import classify_op, engine
    op = classify_op(name)
    if op is not None:
        def _dispatcher(*args, **kwargs):
            return engine.dispatch(op, *args, **kwargs)
        return _dispatcher
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
