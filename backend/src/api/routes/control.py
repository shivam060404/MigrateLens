"""Thin authenticated metadata routes. Execution and publication have no HTTP entry point."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.responses import Response

from src.application.control import CancelCase, CreateBinding, CreateCase
from src.domain.control import AccessDenied, Conflict, ControlUnavailable, NotFound

router = APIRouter(prefix="/tenants/{tenant_id}", tags=["control"])
bearer = HTTPBearer(auto_error=False)


def context(request: Request, credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
    if credentials is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    try:
        principal = request.app.state.token_verifier.verify(credentials.credentials)
    except AccessDenied as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    return request.app.state.control_service, principal


def call(operation, *args):
    try:
        return operation(*args)
    except AccessDenied as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except NotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Conflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ControlUnavailable as exc:
        raise HTTPException(status_code=503, detail="Control database unavailable") from exc


@router.post("/bindings", status_code=201)
def create_binding(tenant_id: UUID, payload: CreateBinding, auth=Depends(context)):
    service, principal = auth
    return call(service.create_binding, principal, tenant_id, payload)


@router.get("/repositories/{repository_id}/bindings")
def list_bindings(
    tenant_id: UUID,
    repository_id: UUID,
    limit: int = Query(50, ge=1, le=100),
    auth=Depends(context),
):
    service, principal = auth
    return call(service.bindings, principal, tenant_id, repository_id, limit)


@router.post("/cases", status_code=201)
def create_case(tenant_id: UUID, payload: CreateCase, auth=Depends(context)):
    service, principal = auth
    return call(service.create_case, principal, tenant_id, payload)


@router.get("/repositories/{repository_id}/cases")
def list_cases(
    tenant_id: UUID,
    repository_id: UUID,
    limit: int = Query(50, ge=1, le=100),
    auth=Depends(context),
):
    service, principal = auth
    return call(service.cases, principal, tenant_id, repository_id, limit)


@router.get("/cases/{case_id}")
def get_case(tenant_id: UUID, case_id: UUID, auth=Depends(context)):
    service, principal = auth
    return call(service.case, principal, tenant_id, case_id)


@router.post("/cases/{case_id}/cancel")
def cancel_case(tenant_id: UUID, case_id: UUID, payload: CancelCase, auth=Depends(context)):
    service, principal = auth
    return call(service.cancel, principal, tenant_id, case_id, payload)


@router.get("/cases/{case_id}/events")
def case_events(
    tenant_id: UUID,
    case_id: UUID,
    after: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    auth=Depends(context),
):
    service, principal = auth
    return call(service.events, principal, tenant_id, case_id, after, limit)


@router.get("/cases/{case_id}/jobs")
def case_jobs(tenant_id: UUID, case_id: UUID, auth=Depends(context)):
    service, principal = auth
    return call(service.jobs, principal, tenant_id, case_id)


@router.get("/artifacts/{artifact_id}")
def artifact_metadata(tenant_id: UUID, artifact_id: UUID, auth=Depends(context)):
    service, principal = auth
    return call(service.artifact, principal, tenant_id, artifact_id)


@router.get("/artifacts/{artifact_id}/download")
def artifact_download(tenant_id: UUID, artifact_id: UUID, auth=Depends(context)):
    service, principal = auth
    content = call(service.download_artifact, principal, tenant_id, artifact_id)
    return Response(
        content=content,
        media_type="application/octet-stream",
        headers={"Cache-Control": "no-store"},
    )
