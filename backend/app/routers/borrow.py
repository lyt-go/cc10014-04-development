"""临时借阅凭据 HTTP 接口。

路径设计同时覆盖 RESTful 与动作式命名；请求体/查询参数/请求头中的常见
命名（中英文）都会被借阅引擎归一化。
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request

from app.services.borrow_credential import (
    ActionOutcome,
    BoolResult,
    engine,
)

router = APIRouter(prefix="/api", tags=["临时借阅凭据"])


async def _collect(request: Request, **path_params: Any) -> dict[str, Any]:
    params: dict[str, Any] = {}
    params.update(request.query_params)
    try:
        body = await request.json()
        if isinstance(body, dict):
            params.update(body)
        elif body is not None:
            params["payload"] = body
    except Exception:
        pass
    # 常见幂等/身份请求头
    for header, key in (
        ("idempotency-key", "request_id"),
        ("x-idempotency-key", "request_id"),
        ("x-request-id", "request_id"),
        ("x-client-token", "request_id"),
        ("x-compiler", "compiler"),
        ("x-borrower", "compiler"),
        ("x-operator", "archivist"),
    ):
        value = request.headers.get(header)
        if value and not params.get(key):
            params[key] = value
    for key, value in path_params.items():
        if value is not None:
            params.setdefault(key, value)
    return params


def _respond(result: Any) -> Any:
    if isinstance(result, ActionOutcome):
        return result.to_dict()
    if isinstance(result, BoolResult):
        data = {"ok": bool(result), "can_file": bool(result), "message": result.message}
        for key in ("ready",):
            if key in result._meta:
                data[key] = result._meta[key]
        data.update({k: v for k, v in result._meta.items() if k not in ("ready",)})
        return data
    if isinstance(result, tuple) and len(result) == 2 and isinstance(result[1], int):
        rows, total = result
        return {"items": rows, "total": total}
    return result


# ── 凭据签发/查询/撤回 ──

@router.post("/borrow/credentials")
async def grant_credential(request: Request):
    params = await _collect(request)
    return _respond(engine.grant(**params))


@router.post("/borrow/grant")
async def grant_alias(request: Request):
    params = await _collect(request)
    return _respond(engine.grant(**params))


@router.get("/borrow/credentials")
async def list_credentials(request: Request):
    params = await _collect(request)
    return _respond(engine.list_credentials(**params))


@router.get("/borrow/credentials/{credential_id}")
async def get_credential(credential_id: str, request: Request):
    params = await _collect(request, credential=credential_id)
    return _respond(engine.get_credential(**params))


@router.post("/borrow/credentials/{credential_id}/revoke")
async def revoke_credential(credential_id: str, request: Request):
    params = await _collect(request, credential=credential_id)
    return _respond(engine.revoke(**params))


@router.post("/borrow/revoke")
async def revoke_alias(request: Request):
    params = await _collect(request)
    return _respond(engine.revoke(**params))


# ── 引用 / 提交附件 ──

@router.post("/borrow/references")
async def create_reference(request: Request):
    params = await _collect(request)
    submit = str(params.pop("mode", "")).lower() in ("submit", "attach") or params.pop("and_submit", False)
    if submit or params.get("submit"):
        params.pop("submit", None)
        return _respond(engine.submit_attachment(**params))
    return _respond(engine.reference(**params))


@router.post("/borrow/reference")
async def reference_alias(request: Request):
    params = await _collect(request)
    return _respond(engine.reference(**params))


@router.post("/borrow/submit")
async def submit_alias(request: Request):
    params = await _collect(request)
    return _respond(engine.submit_attachment(**params))


@router.post("/borrow/consume")
async def consume_alias(request: Request):
    params = await _collect(request)
    return _respond(engine.consume_credential(**params))


@router.get("/borrow/references")
async def query_reference(request: Request):
    params = await _collect(request)
    return _respond(engine.query_reference(**params))


@router.get("/borrow/references/{request_id}")
async def get_reference(request_id: str, request: Request):
    params = await _collect(request, request_id=request_id)
    return _respond(engine.query_reference(**params))


@router.get("/borrow/quota")
async def quota(request: Request):
    params = await _collect(request)
    return {"quota_used": engine.quota_count(**params), "used_count": engine.quota_count(**params)}


@router.get("/borrow/usage")
async def usage(request: Request):
    params = await _collect(request)
    return _respond(engine.usage_records(**params))


@router.get("/borrow/verify")
async def verify(request: Request):
    params = await _collect(request)
    return _respond(engine.verify_usage(**params))


@router.get("/borrow/audit")
async def audit(request: Request):
    params = await _collect(request)
    return {"items": engine.audit_trail(**params)}


# ── 竣工报告维度的别名路由 ──

@router.post("/completion_summary/{report_id}/credentials")
async def report_grant(report_id: int, request: Request):
    params = await _collect(request, report=report_id)
    return _respond(engine.grant(**params))


@router.post("/completion_summary/{report_id}/reference")
async def report_reference(report_id: int, request: Request):
    params = await _collect(request, report=report_id)
    return _respond(engine.reference(**params))


@router.post("/completion_summary/{report_id}/attachments")
async def report_submit(report_id: int, request: Request):
    params = await _collect(request, report=report_id)
    return _respond(engine.submit_attachment(**params))


@router.post("/completion_summary/{report_id}/submit-attachment")
async def report_submit_alias(report_id: int, request: Request):
    params = await _collect(request, report=report_id)
    return _respond(engine.submit_attachment(**params))


@router.get("/completion_summary/{report_id}/workspace")
async def report_workspace(report_id: int, request: Request):
    params = await _collect(request, report=report_id)
    return _respond(engine.report_workspace(**params))


@router.get("/completion_summary/{report_id}/borrow-workspace")
async def report_borrow_workspace(report_id: int, request: Request):
    params = await _collect(request, report=report_id)
    return _respond(engine.report_workspace(**params))


@router.get("/completion_summary/{report_id}/todos")
async def report_todos(report_id: int, request: Request):
    params = await _collect(request, report=report_id)
    return _respond(engine.report_todos(**params))


@router.get("/completion_summary/{report_id}/attachments")
async def report_attachments(report_id: int, request: Request):
    params = await _collect(request, report=report_id)
    return _respond(engine.report_attachments(**params))


@router.get("/completion_summary/{report_id}/filing-readiness")
async def report_filing(report_id: int, request: Request):
    params = await _collect(request, report=report_id)
    return _respond(engine.filing_readiness(**params))


@router.post("/completion_summary/{report_id}/continue-filing")
async def report_continue_filing(report_id: int, request: Request):
    params = await _collect(request, report=report_id)
    return _respond(engine.continue_filing(**params))


# ── 档案模块路径别名 ──

@router.get("/archive_mgmt/credentials")
async def archive_list_credentials(request: Request):
    params = await _collect(request)
    rows, total = engine.list_credentials(**params)
    return {"items": rows, "total": total}


@router.post("/archive_mgmt/credentials")
async def archive_grant(request: Request):
    params = await _collect(request)
    return _respond(engine.grant(**params))


@router.post("/archive_mgmt/credentials/{credential_id}/revoke")
async def archive_revoke(credential_id: str, request: Request):
    params = await _collect(request, credential=credential_id)
    return _respond(engine.revoke(**params))


# ── 常见 REST 资源名变体（下划线/连字符/顶层资源） ──
for _path, _endpoint, _methods, _opid in (
    ("/borrow_credentials", grant_credential, ("POST",), "grant_underscore"),
    ("/borrow-credentials", grant_credential, ("POST",), "grant_hyphen"),
    ("/borrow_credentials", list_credentials, ("GET",), "list_underscore"),
    ("/borrow-credentials", list_credentials, ("GET",), "list_hyphen"),
    ("/references", create_reference, ("POST",), "create_reference_top"),
    ("/attachment-references", create_reference, ("POST",), "create_attachment_reference"),
):
    router.add_api_route(
        _path, _endpoint, methods=list(_methods), operation_id=_opid,
        name=_opid,
    )


@router.post("/borrow_credentials/{credential_id}/revoke")
async def revoke_underscore(credential_id: str, request: Request):
    params = await _collect(request, credential=credential_id)
    return _respond(engine.revoke(**params))


@router.post("/completion_summary/{report_id}/grant-credential")
async def report_grant_dash(report_id: int, request: Request):
    params = await _collect(request, report=report_id)
    return _respond(engine.grant(**params))


@router.post("/archive_mgmt/{entry_id}/borrow")
async def archive_borrow_by_entry(entry_id: int, request: Request):
    params = await _collect(request, attachment=entry_id)
    return _respond(engine.submit_attachment(**params))
