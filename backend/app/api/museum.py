from fastapi import APIRouter, HTTPException, Response, status

from app.api.deps import CurrentAdminUser, SessionDep
from app.application.museum_profile_service import (
    MuseumConfigurationConflict,
    get_museum_configuration,
    save_museum_configuration,
)
from app.config.settings import get_settings
from app.domain.museum_profile import (
    MuseumConfiguration,
    MuseumConfigurationUpdate,
    PublicMuseumConfiguration,
    public_museum_configuration,
)

router = APIRouter(tags=["museum"])


@router.get("/museum/bootstrap", response_model=PublicMuseumConfiguration)
async def museum_bootstrap(session: SessionDep, response: Response) -> PublicMuseumConfiguration:
    response.headers["Cache-Control"] = "no-store"
    return public_museum_configuration(await get_museum_configuration(session))


@router.get("/admin/museum", response_model=MuseumConfiguration)
async def read_museum_configuration(
    session: SessionDep, admin: CurrentAdminUser, response: Response,
) -> MuseumConfiguration:
    response.headers["Cache-Control"] = "no-store"
    return await get_museum_configuration(session)


@router.get("/admin/museum/export", response_model=MuseumConfiguration)
async def export_museum_configuration(
    session: SessionDep, admin: CurrentAdminUser, response: Response,
) -> MuseumConfiguration:
    response.headers["Cache-Control"] = "no-store"
    response.headers["Content-Disposition"] = 'attachment; filename="museum-profile.json"'
    return await get_museum_configuration(session)


@router.put("/admin/museum", response_model=MuseumConfiguration)
@router.post("/admin/museum/import", response_model=MuseumConfiguration)
async def write_museum_configuration(
    payload: MuseumConfigurationUpdate, session: SessionDep, admin: CurrentAdminUser, response: Response,
) -> MuseumConfiguration:
    response.headers["Cache-Control"] = "no-store"
    expected_id = get_settings().EXPECTED_MUSEUM_ID
    if get_settings().MUSEUM_SELF_SERVICE_IMPORT:
        from app.infra.postgres.models import MuseumInstallation
        installation = await session.get(MuseumInstallation, 1)
        if not installation or installation.status != "ready":
            raise HTTPException(409, detail="请先在资料包导入页面完成本馆初始化。")
        expected_id = installation.museum_id
    if expected_id and payload.museum.museum_id != expected_id:
        raise HTTPException(status_code=422, detail="独立部署的馆 ID 不可更改；新博物馆请创建新实例。")
    try:
        return await save_museum_configuration(session, payload)
    except MuseumConfigurationConflict as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
