"""Validate portable museum packages, then bootstrap ONLY unused deployments.

Existing museums keep using the authenticated administration APIs. This is not
an overwrite/import-all tool. A partially completed bootstrap can be retried
with exactly the same package; a finished bootstrap is an idempotent no-op.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from uuid import NAMESPACE_URL, uuid5

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, func, select

from app.api.documents import KnowledgeMetadata, validate_knowledge_content
from app.application.content_source import ContentMetadata, ContentSource
from app.application.document_service import update_document_status
from app.application.museum_data_import_service import MuseumDataImportService, MuseumDataset, load_museum_dataset
from app.application.museum_profile_service import get_museum_configuration, save_museum_configuration
from app.domain.museum_profile import MuseumConfiguration, MuseumConfigurationUpdate
from app.domain.tts_config import DEFAULT_TTS_STYLE
from app.infra.postgres.adapters.document_repository import PostgresDocumentRepository
from app.infra.postgres.models import Base, Document, Hall, IngestionJob, MuseumInstallation, Prompt, User


class PackageError(ValueError):
    """Operator-safe validation failure (no credentials or connection URLs)."""


class KnowledgeEntry(KnowledgeMetadata):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]*$", max_length=64)
    file: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=1, max_length=255)
    source_label: str = Field(min_length=1, max_length=500)


class PackageManifest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal[1]
    museum_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]*$", max_length=64)
    knowledge: list[KnowledgeEntry] = Field(default_factory=list, max_length=1000)
    images: list["PackageImage"] = Field(default_factory=list, max_length=500)


class PackageImage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_record_id: str = Field(min_length=1, max_length=255)
    file: str = Field(min_length=1, max_length=255)


PackageManifest.model_rebuild()


@dataclass(frozen=True)
class MuseumPackage:
    manifest: PackageManifest
    configuration: MuseumConfiguration
    dataset: MuseumDataset
    contents: dict[str, str]
    digest: str
    root: Path | None = None

    @property
    def source_name(self) -> str:
        return f"museum:{self.manifest.museum_id}"


def safe_package_file(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if Path(relative).is_absolute() or not path.is_relative_to(root.resolve()) or not path.is_file():
        raise PackageError("Package file must exist inside its directory")
    if path.stat().st_size > 50 * 1024 * 1024:
        raise PackageError("Each package file must be at most 50 MB")
    return path


def load_package(root: Path) -> MuseumPackage:
    root = root.resolve()
    files = {
        name: safe_package_file(root, name).read_bytes()
        for name in ("manifest.json", "profile.json", "halls.csv", "exhibits.csv")
    }
    manifest = PackageManifest.model_validate_json(files["manifest.json"])
    raw_profile = json.loads(files["profile.json"].decode("utf-8-sig"))
    # Do not silently bring the old museum's business defaults into a new package.
    from app.domain.business_config import MuseumBusinessConfig

    required_sections = set(MuseumBusinessConfig.model_fields) - {"visitor_experience"}
    if required_sections - set(raw_profile.get("museum", {}).get("business", {})):
        raise PackageError("profile.json must explicitly contain all museum.business sections")
    configuration = MuseumConfiguration.model_validate(raw_profile)
    if configuration.museum.museum_id != manifest.museum_id:
        raise PackageError("Manifest museum_id must match profile.json")
    dataset = load_museum_dataset(root)
    exhibit_by_source = {item.source_record_id: item for item in dataset.exhibits}
    active_halls = {hall.slug for hall in dataset.halls if hall.is_active}
    if not active_halls:
        raise PackageError("A deployable package needs at least one active hall")
    categories = {item.value for item in configuration.museum.business.categories}
    for exhibit in dataset.exhibits:
        if exhibit.category not in categories:
            raise PackageError(f"Unknown category for exhibit {exhibit.source_record_id}")
    for code, route in configuration.museum.business.routes.items():
        if set(route.preferred_halls) - active_halls:
            raise PackageError(f"Route {code} references missing/inactive halls")
    experience = configuration.museum.business.visitor_experience
    if experience:
        if set(experience.hall_openings) - active_halls:
            raise PackageError("Visitor opening references a missing/inactive hall")
        for card in experience.exhibits:
            exhibit = exhibit_by_source.get(card.source_record_id)
            if not exhibit or not exhibit.is_active or exhibit.hall != card.hall_slug:
                raise PackageError("Visitor card does not match its active exhibit")
            if set(card.related_ids) - set(exhibit_by_source):
                raise PackageError("Visitor card references unknown related exhibits")
        for route in experience.routes:
            stops = list(route.steps) + [stop for variant in route.interest_variants.values() for stop in variant]
            for stop in stops:
                if stop.hall_slug not in active_halls:
                    raise PackageError("Visitor route references unavailable hall")
                if any(
                    eid not in exhibit_by_source or not exhibit_by_source[eid].is_active
                    or exhibit_by_source[eid].hall != stop.hall_slug for eid in stop.exhibit_ids
                ):
                    raise PackageError("Visitor route exhibit does not belong to its hall")
    seen_images = set()
    from app.application.exhibit_images import _inspect_image

    for item in manifest.images:
        if item.source_record_id not in exhibit_by_source or item.source_record_id in seen_images:
            raise PackageError("Duplicate or unknown exhibit image identity")
        seen_images.add(item.source_record_id)
        path = safe_package_file(root, item.file)
        if path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"} or path.stat().st_size > 10 * 1024 * 1024:
            raise PackageError("Package images must be PNG, JPEG or WebP, at most 10 MB")
        _inspect_image(path, max_pixels=20_000_000)
        files[item.file] = path.read_bytes()
    contents = {}
    for item in manifest.knowledge:
        if item.id in contents:
            raise PackageError("Duplicate knowledge id")
        if item.hall_slug and item.hall_slug not in active_halls:
            raise PackageError(f"Knowledge {item.id} references a missing/inactive hall")
        path = safe_package_file(root, item.file)
        if path.suffix.lower() not in {".txt", ".md", ".markdown"}:
            raise PackageError("Knowledge files must be UTF-8 TXT or Markdown")
        files[item.file] = path.read_bytes()
        contents[item.id] = validate_knowledge_content(files[item.file].decode("utf-8-sig"))
    digest = hashlib.sha256()
    for name, content in sorted(files.items()):
        digest.update(name.encode())
        digest.update(b"\0")
        digest.update(hashlib.sha256(content).digest())
    return MuseumPackage(manifest, configuration, dataset, contents, digest.hexdigest(), root)


async def verify_installation(session, museum_id: str, search_index: str) -> None:
    record = await session.get(MuseumInstallation, 1)
    config = await get_museum_configuration(session)
    if (
        record is None
        or record.status != "ready"
        or record.museum_id != museum_id
        or record.search_index != search_index
        or config.museum.museum_id != museum_id
    ):
        raise PackageError("Museum is not initialized or its identity/index does not match this deployment")


async def require_unused_database(session) -> None:
    # Future business tables are also protected by default. Only immutable
    # migration-seeded tables and the empty installation table are exempt.
    seeded = {"halls", "prompts", "prompt_versions", "museum_installation"}
    for table in Base.metadata.sorted_tables:
        if table.name not in seeded and (await session.execute(select(func.count()).select_from(table))).scalar_one():
            raise PackageError(f"Refusing to initialize an existing database: {table.name} is not empty")
    # Load the immutable migration's precise seed instead of guessing which
    # user-created halls are safe to remove.
    migration = Path(__file__).parents[2] / "alembic/versions/20260808_remove_unreferenced_legacy_halls.py"
    spec = importlib.util.spec_from_file_location("_museum_seed_baseline", migration)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    baseline = {row["slug"]: row for row in module.CANONICAL_HALL_BASELINE}
    for hall in (await session.execute(select(Hall))).scalars():
        seed = baseline.get(hall.slug)
        if (
            not seed
            or hall.source_name
            or hall.aliases
            or hall.suggested_questions
            or any(getattr(hall, key) != value for key, value in seed.items())
        ):
            raise PackageError("Existing halls differ from migration seeds; use a new database")


async def initialize_package(session, package: MuseumPackage, indexer, *, admin_email: str, password_hash: str,
                             portal_admin_id: str | None = None, progress=None) -> dict:
    """The CLI holds a PostgreSQL session advisory lock throughout this call."""
    record = await session.get(MuseumInstallation, 1)
    index_name = indexer.es_client.index_name
    if portal_admin_id and record and record.status == "awaiting_import":
        # Only the explicitly provisioned empty portal can bind its first museum.
        from app.infra.postgres.models import Exhibit, TourSessionModel
        for model in (Document, Exhibit, Hall, TourSessionModel):
            if (await session.execute(select(func.count()).select_from(model))).scalar_one():
                raise PackageError("空白馆已有业务数据，请使用新的空白实例导入。")
        if record.search_index != index_name:
            raise PackageError("导入实例的索引不匹配。")
        if await indexer.es_client.client.indices.exists(index=index_name):
            if (await indexer.es_client.client.count(index=index_name))["count"]:
                raise PackageError("空白馆搜索索引已有内容。")
        record.museum_id = package.manifest.museum_id
        record.package_digest = package.digest
        record.status = "initializing"
        current = await get_museum_configuration(session)
        await save_museum_configuration(session, MuseumConfigurationUpdate(
            schema_version=1, expected_revision=current.revision, museum=package.configuration.museum,
        ))
        await session.commit()
    if record:
        if (
            record.museum_id != package.manifest.museum_id
            or record.package_digest != package.digest
            or record.search_index != index_name
        ):
            raise PackageError("Deployment already belongs to another package/index; use administration for updates")
        if record.status == "ready":
            await verify_installation(session, record.museum_id, index_name)
            return {"status": "already_initialized", "museum_id": record.museum_id}
    else:
        await require_unused_database(session)
        if await indexer.es_client.client.indices.exists(index=index_name):
            count = await indexer.es_client.client.count(index=index_name)
            if count["count"]:
                raise PackageError("Search index is not empty; use a separate index")
        await indexer.es_client.create_index(index_name, indexer.embeddings_dimension)
        await session.execute(delete(Hall))
        # Historical voice seeds describe Banpo; new installations start with
        # the same generic voice policy as the business configuration.
        for prompt in (await session.execute(select(Prompt))).scalars():
            if prompt.key.startswith("tour_tts_persona_"):
                prompt.content = DEFAULT_TTS_STYLE
                prompt.variables = []
        session.add(
            User(
                id=str(uuid5(NAMESPACE_URL, package.source_name + ":admin")),
                email=admin_email,
                password_hash=password_hash,
                role="admin",
            )
        )
        await save_museum_configuration(
            session,
            MuseumConfigurationUpdate(
                schema_version=1,
                expected_revision=0,
                museum=package.configuration.museum,
            ),
        )
        record = MuseumInstallation(
            id=1,
            museum_id=package.manifest.museum_id,
            package_digest=package.digest,
            search_index=index_name,
            status="initializing",
        )
        session.add(record)
        await session.commit()
    if progress:
        await progress("catalog", 0, len(package.contents), "正在导入展厅、展品并建立展品索引")
    await MuseumDataImportService(session, indexer).import_dataset(package.dataset, source_name=package.source_name)
    if package.manifest.images:
        from app.application.exhibit_images import ExhibitImageStorage
        from app.config.settings import get_settings
        from app.infra.postgres.models import Exhibit

        settings = get_settings()
        storage = ExhibitImageStorage(
            settings.EXHIBIT_IMAGE_DIR,
            max_bytes=settings.EXHIBIT_IMAGE_MAX_BYTES,
            max_pixels=settings.EXHIBIT_IMAGE_MAX_PIXELS,
        )
        for image in package.manifest.images:
            exhibit = (await session.execute(select(Exhibit).where(
                Exhibit.source_name == package.source_name, Exhibit.source_record_id == image.source_record_id,
            ))).scalar_one()
            source = safe_package_file(package.root, image.file)
            checksum = hashlib.sha256(source.read_bytes()).hexdigest()[:20]
            relative = f"{exhibit.id}/package-{checksum}{source.suffix.lower()}"
            destination = storage.resolve(relative)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
            exhibit.image_path = relative
        await session.commit()
    admin = await session.get(User, portal_admin_id) if portal_admin_id else (
        await session.execute(select(User).where(User.role == "admin"))
    ).scalars().first()
    for position, entry in enumerate(package.manifest.knowledge):
        if progress:
            await progress("knowledge", position, len(package.contents), "正在索引：" + entry.title)
        doc_id = str(uuid5(NAMESPACE_URL, package.source_name + ":knowledge:" + entry.id))
        document = await session.get(Document, doc_id)
        if document is None:
            document = Document(
                id=doc_id,
                user_id=admin.id,
                filename=Path(entry.file).name,
                content_text=package.contents[entry.id],
                status="pending",
                **entry.model_dump(exclude={"id", "file"}),
            )
            session.add(document)
            session.add(IngestionJob(id=str(uuid5(NAMESPACE_URL, doc_id)), document_id=doc_id, status="pending"))
            await session.commit()
        if document.status == "completed" and document.indexed_revision == document.revision:
            continue
        document.indexed_revision = 0
        await session.commit()
        await indexer.delete_source(doc_id, source_type="document")
        count = await indexer.index_source(
            ContentSource(
                source_id=doc_id,
                source_type="document",
                content=document.content_text,
                metadata=ContentMetadata(filename=document.filename, extra={
                    "knowledge_revision": document.revision, "title": document.title,
                    "source_label": document.source_label, "hall": document.hall_slug,
                }),
            )
        )
        if count <= 0:
            raise PackageError("Knowledge indexing produced no chunks; retry after fixing embeddings")
        await indexer.refresh_index()
        document.indexed_revision = document.revision
        await update_document_status(PostgresDocumentRepository(session), doc_id, "completed", None, count)
        await session.commit()
    await indexer.refresh_index()
    record.status = "ready"
    await session.commit()
    return {
        "status": "initialized",
        "museum_id": record.museum_id,
        "halls": len(package.dataset.halls),
        "exhibits": len(package.dataset.exhibits),
        "knowledge_documents": len(package.contents),
    }
