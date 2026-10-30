"""Authenticated preview/confirm/progress workflow for a provisioned empty museum."""
import asyncio
import json
import os
import uuid
from pathlib import Path
from zipfile import BadZipFile
import shutil

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile
from loguru import logger
from pydantic import ValidationError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentAdminUser, SessionDep, UnifiedIndexingServiceDep
from app.application.museum_import_archive import MAX_ARCHIVE_BYTES, extract_package
from app.application.museum_package import PackageError, initialize_package, load_package
from app.config.settings import get_settings
from app.infra.postgres.database import get_session_maker
from app.infra.postgres.models import MuseumInstallation

router = APIRouter(tags=["museum-import"])


def job_directory(job_id: str) -> Path:
    try:
        value = str(uuid.UUID(job_id))
    except ValueError:
        raise HTTPException(404, "导入任务不存在") from None
    return Path(get_settings().EXHIBIT_IMAGE_DIR).resolve().parent / "museum-imports" / value


def save_job(directory, job):
    temporary = directory / ("job-" + uuid.uuid4().hex + ".tmp")
    temporary.write_text(json.dumps(job, ensure_ascii=False), encoding="utf-8")
    os.replace(temporary, directory / "job.json")


def read_job(job_id, admin):
    directory = job_directory(job_id)
    try:
        job = json.loads((directory / "job.json").read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        raise HTTPException(404, "导入任务不存在") from None
    if job["owner"] != admin["id"]:
        raise HTTPException(404, "导入任务不存在")
    return directory, job


def public_job(job):
    return {k: v for k, v in job.items() if k not in {"owner", "package_root"}}


@router.get("/museum/import-status")
async def import_status(session: SessionDep):
    if not get_settings().MUSEUM_SELF_SERVICE_IMPORT:
        return {"status": "ready", "self_service": False}
    record = await session.get(MuseumInstallation, 1)
    return {"status": record.status if record else "unprepared", "self_service": True}


@router.post("/admin/museum/packages/preview")
async def preview_package(session: SessionDep, admin: CurrentAdminUser, file: UploadFile = File(...)):
    if not get_settings().MUSEUM_SELF_SERVICE_IMPORT:
        raise HTTPException(409, "请在新建的馆方导入实例中操作；当前实例继续使用现有后台维护。")
    if not (file.filename or "").lower().endswith(".zip"):
        raise HTTPException(422, "请上传标准资料包 ZIP。")
    record = await session.get(MuseumInstallation, 1)
    if not record:
        raise HTTPException(409, "请先初始化空白馆后台。")
    job_id = str(uuid.uuid4())
    directory = job_directory(job_id)
    directory.mkdir(parents=True)
    archive = directory / "upload.zip"
    size = 0
    staged = False
    try:
        with archive.open("xb") as output:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_ARCHIVE_BYTES:
                    raise HTTPException(413, "ZIP 最大为 100 MB。")
                output.write(chunk)
        package = await asyncio.to_thread(extract_package, archive, directory / "package")
        if record.status != "awaiting_import" and record.package_digest != package.digest:
            raise HTTPException(409, "本馆已绑定其他资料包。导入后的修改请使用知识库、展厅、展品和馆方配置页面；另一家馆请使用新实例。")
        job = {
            "id": job_id, "owner": admin["id"], "status": "preview", "phase": "validated",
            "package_root": str(package.root), "digest": package.digest,
            "museum_id": package.manifest.museum_id, "museum_name": package.configuration.museum.name,
            "halls": [{"name": h.name, "slug": h.slug} for h in package.dataset.halls],
            "exhibits": [{"id": e.source_record_id, "name": e.name, "hall": e.hall} for e in package.dataset.exhibits],
            "documents": [{"title": k.title, "source_label": k.source_label} for k in package.manifest.knowledge],
            "image_count": len(package.manifest.images),
            "route_count": len(package.configuration.museum.business.visitor_experience.routes) if package.configuration.museum.business.visitor_experience else 0,
            "completed": 0, "total": len(package.contents), "message": "校验通过，尚未写入馆藏资料。",
        }
        save_job(directory, job)
        staged = True
        return public_job(job)
    except (PackageError, ValidationError, BadZipFile, ValueError) as exc:
        message = str(exc)[:1800]
        raise HTTPException(422, "资料包校验失败：" + message) from None
    finally:
        await file.close()
        if not staged and directory.resolve() == job_directory(job_id).resolve():
            shutil.rmtree(directory)


async def run_import(directory, job, indexer, admin):
    maker = get_session_maker()
    engine = maker.kw["bind"]
    async with engine.connect() as connection:
        locked = (await connection.execute(text("SELECT pg_try_advisory_lock(682417236)"))).scalar_one()
        await connection.commit()
        if not locked:
            return
        try:
            async with AsyncSession(connection, expire_on_commit=False) as session:
                async def progress(phase, completed, total, message):
                    job.update(status="running", phase=phase, completed=completed, total=total, message=message)
                    save_job(directory, job)
                package = await asyncio.to_thread(load_package, Path(job["package_root"]))
                if package.digest != job["digest"]:
                    raise PackageError("预览后的资料发生变化，请重新上传。")
                await progress("starting", 0, len(package.contents), "开始导入资料")
                result = await initialize_package(session, package, indexer, admin_email=admin["email"],
                    password_hash="unused", portal_admin_id=admin["id"], progress=progress)
                job.update(status="completed", phase="completed", completed=job["total"], message="资料导入和索引已完成，可进入游客端。", result=result)
        except Exception:
            logger.exception("Museum import failed: {}", job["id"])
            job.update(status="failed", message="导入未完成。请检查模型与检索服务后点击重试；已完成的数据可继续复用。")
        finally:
            save_job(directory, job)
            await connection.rollback()
            await connection.execute(text("SELECT pg_advisory_unlock(682417236)"))
            await connection.commit()


@router.post("/admin/museum/packages/{job_id}/confirm")
async def confirm_package(job_id: str, session: SessionDep, admin: CurrentAdminUser,
                          indexer: UnifiedIndexingServiceDep, background: BackgroundTasks):
    directory, job = read_job(job_id, admin)
    if not get_settings().MUSEUM_SELF_SERVICE_IMPORT:
        raise HTTPException(409, "当前实例未启用馆方导入。")
    record = await session.get(MuseumInstallation, 1)
    if not record or (record.status != "awaiting_import" and record.package_digest != job["digest"]):
        raise HTTPException(409, "实例已绑定其他资料包，请重新查看当前馆状态。")
    if job["status"] != "completed":
        background.add_task(run_import, directory, job, indexer, admin)
    return public_job(job)


@router.get("/admin/museum/packages/{job_id}")
async def package_progress(job_id: str, admin: CurrentAdminUser):
    _, job = read_job(job_id, admin)
    return public_job(job)
