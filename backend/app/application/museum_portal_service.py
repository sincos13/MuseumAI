"""Provision an empty curator portal without importing any museum content."""
from uuid import uuid4

from sqlalchemy import delete, select

from app.application.museum_package import PackageError, require_unused_database
from app.application.museum_profile_service import save_museum_configuration
from app.domain.museum_profile import MuseumConfigurationUpdate, default_museum_profile
from app.domain.tts_config import DEFAULT_TTS_STYLE
from app.infra.postgres.models import Hall, MuseumInstallation, Prompt, User


async def provision_empty_portal(session, *, search_index, email, password_hash):
    record = await session.get(MuseumInstallation, 1)
    if record:
        if record.search_index != search_index:
            raise PackageError("Portal database/index identity mismatch")
        return False
    await require_unused_database(session)
    await session.execute(delete(Hall))
    profile = default_museum_profile().model_copy(update={
        "museum_id": "unconfigured", "name": "馆方资料导入中心", "short_name": "待配置博物馆",
        "description": "这是尚未导入馆藏资料的空白实例。请登录后台上传标准资料包。",
    })
    await save_museum_configuration(session, MuseumConfigurationUpdate(
        schema_version=1, expected_revision=0, museum=profile,
    ))
    session.add(User(id=str(uuid4()), email=email, password_hash=password_hash, role="admin"))
    session.add(MuseumInstallation(id=1, museum_id="unconfigured", package_digest="",
        search_index=search_index, status="awaiting_import"))
    for prompt in (await session.execute(select(Prompt))).scalars():
        if prompt.key.startswith("tour_tts_persona_"):
            prompt.content = DEFAULT_TTS_STYLE
            prompt.variables = []
    await session.flush()
    return True
