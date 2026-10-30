#!/usr/bin/env python3
"""Portable package validation, deployment files, bootstrap and source audit."""
# ruff: noqa: E402

import argparse
import asyncio
import getpass
import json
import os
import re
import secrets
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))

from app.application.museum_data_import_service import MuseumDataValidationError
from app.application.museum_package import PackageError, initialize_package, load_package, verify_installation
from app.config.settings import Settings
from pydantic import ValidationError
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine


def create_environment(package, output: Path, *, port: int, llm_model: str, embedding_model: str, dims: int, self_service: bool = False) -> dict:
    if output.exists():
        raise PackageError("Output directory already exists; refusing to replace credentials")
    museum_id = "portal-" + secrets.token_hex(4) if self_service else package.manifest.museum_id
    # Compose names exclude underscores even though museum identity permits them.
    project = "museum-" + museum_id.replace("_", "-") + "-" + secrets.token_hex(3)
    db_password = secrets.token_hex(24)
    settings = {
        "APP_ENV": "local",
        "DEBUG": "false",
        "EXPECTED_MUSEUM_ID": "" if self_service else museum_id,
        "MUSEUM_SELF_SERVICE_IMPORT": "true" if self_service else "false",
        "DATABASE_URL": f"postgresql+asyncpg://museai:{db_password}@postgres:5432/museai",
        "POSTGRES_USER": "museai",
        "POSTGRES_PASSWORD": db_password,
        "POSTGRES_DB": "museai",
        "REDIS_URL": "redis://redis:6379/0",
        "ELASTICSEARCH_URL": "http://elasticsearch:9200",
        "ELASTICSEARCH_INDEX": "museum_" + museum_id.replace("-", "_") + "_v1",
        "JWT_SECRET": secrets.token_hex(32),
        "LLM_PROVIDER": "openai_compatible",
        "LLM_COMPAT_MODE": "openai",
        "LLM_BASE_URL": "http://host.docker.internal:11434/v1",
        "LLM_API_KEY": "ollama-local",
        "LLM_MODEL": llm_model,
        "LLM_TOUR_MODEL": llm_model,
        "LLM_REPORT_MODEL": llm_model,
        "EMBEDDING_PROVIDER": "ollama",
        "EMBEDDING_OLLAMA_BASE_URL": "http://host.docker.internal:11434",
        "EMBEDDING_OLLAMA_MODEL": embedding_model,
        "EMBEDDING_DIMS": str(dims),
        "RERANK_PROVIDER": "mock",
        "TTS_ENABLED": "false",
        "CORS_ORIGINS": f"http://127.0.0.1:{port},http://localhost:{port}",
        "EXHIBIT_IMAGE_DIR": "/app/var/exhibit-images",
    }
    # No model keys, passwords or URLs are printed to the terminal.
    Settings(_env_file=None, **settings)
    output.mkdir(parents=True)
    for filename, values in {
        "app.env": settings,
        "instance.env": {
            "COMPOSE_PROJECT_NAME": project,
            "MUSEUM_HTTP_PORT": str(port),
            "MUSEUM_BIND_ADDRESS": "127.0.0.1",
            "POSTGRES_PASSWORD": db_password,
        },
    }.items():
        path = output / filename
        path.write_text("\n".join(f"{key}={value}" for key, value in values.items()) + "\n", encoding="utf-8")
        path.chmod(0o600)
    return {
        "status": "environment_created",
        "directory": str(output),
        "museum_id": museum_id,
        "visitor_url": f"http://127.0.0.1:{port}/tour",
        "note": "Local text demo: configure real reranking and TTS providers before production acceptance",
    }


def new_admin_password_hash() -> str:
    """Explain password policy, retry console input, and never echo credentials."""
    from app.infra.security.password import hash_password
    from bootstrap_admin import MIN_PASSWORD_LENGTH, _validate_password

    password = os.environ.get("MUSEAI_ADMIN_PASSWORD")
    interactive = password is None
    if interactive:
        if not sys.stdin.isatty():
            raise PackageError(
                "Run initialization in an interactive terminal to enter the admin password, "
                "or set MUSEAI_ADMIN_PASSWORD for unattended initialization"
            )
        print(
            f"Admin password: at least {MIN_PASSWORD_LENGTH} characters, including uppercase, "
            "lowercase, a digit and a special character. Input is hidden.",
            file=sys.stderr,
            flush=True,
        )
    while True:
        if interactive:
            password = getpass.getpass("New admin password: ")
        try:
            _validate_password(password)
        except ValueError as exc:
            # This validator emits controlled policy text, never the password.
            if not interactive:
                raise PackageError(f"Invalid MUSEAI_ADMIN_PASSWORD: {exc}") from None
            print(f"Invalid admin password: {exc}. Please try again.", file=sys.stderr, flush=True)
            continue
        return hash_password(password)


async def operate(args, settings):
    from app.application.unified_indexing_service import UnifiedIndexingService
    from app.infra.elasticsearch.client import ElasticsearchClient
    from app.infra.langchain import create_embeddings
    from app.infra.postgres.models import Document, Exhibit, Hall, MuseumInstallation, Prompt

    if not settings.DATABASE_URL.startswith("postgresql+asyncpg://"):
        raise PackageError("Independent deployments require PostgreSQL (asyncpg)")
    if not settings.EXPECTED_MUSEUM_ID:
        raise PackageError("EXPECTED_MUSEUM_ID is required for independent deployment commands")
    engine = create_async_engine(settings.DATABASE_URL)
    es = ElasticsearchClient([settings.ELASTICSEARCH_URL], index_name=settings.ELASTICSEARCH_INDEX)
    try:
        async with engine.connect() as connection:
            if args.command == "initialize":
                # Session-scoped lock survives importer commits. Never run two
                # initializers in the same database concurrently.
                locked = (await connection.execute(text("SELECT pg_try_advisory_lock(682417236)"))).scalar_one()
                await connection.commit()
                if not locked:
                    raise PackageError("Another initializer is running")
                try:
                    package = load_package(args.package)
                    if package.manifest.museum_id != settings.EXPECTED_MUSEUM_ID:
                        raise PackageError("Package museum_id differs from EXPECTED_MUSEUM_ID")
                    from pydantic import TypeAdapter
                    from pydantic.networks import EmailStr

                    email = str(TypeAdapter(EmailStr).validate_python(args.admin_email))
                    async with AsyncSession(connection, expire_on_commit=False) as session:
                        record = await session.get(MuseumInstallation, 1)
                        if record:
                            # Repeating a completed run never resets credentials.
                            password_hash = "unused-for-resume"
                        else:
                            password_hash = new_admin_password_hash()
                        if not await es.health_check():
                            raise PackageError("Elasticsearch is unavailable")
                        try:
                            embeddings = create_embeddings(settings)
                            vector = await embeddings.aembed_query("博物馆连接检查")
                        except Exception as exc:
                            # Provider exceptions can include URLs and credentials.
                            raise PackageError(
                                f"Embedding connection check failed ({type(exc).__name__}). "
                                "Check the instance EMBEDDING_* settings and model service, "
                                "then retry the same package"
                            ) from None
                        if len(vector) != settings.EMBEDDING_DIMS:
                            raise PackageError("Embedding dimension differs from EMBEDDING_DIMS")
                        indexer = UnifiedIndexingService(es, embeddings)
                        indexer.embeddings_dimension = settings.EMBEDDING_DIMS
                        return await initialize_package(
                            session, package, indexer, admin_email=email, password_hash=password_hash
                        )
                finally:
                    await connection.rollback()
                    await connection.execute(text("SELECT pg_advisory_unlock(682417236)"))
                    await connection.commit()
            async with AsyncSession(connection) as session:
                await verify_installation(session, settings.EXPECTED_MUSEUM_ID, settings.ELASTICSEARCH_INDEX)
                halls = list((await session.execute(select(Hall).where(Hall.is_active.is_(True)))).scalars())
                exhibits = list((await session.execute(select(Exhibit).where(Exhibit.is_active.is_(True)))).scalars())
                docs = list((await session.execute(select(Document))).scalars())
                prompts = list((await session.execute(select(Prompt).where(Prompt.is_active.is_(True)))).scalars())
                warnings = [
                    "Active prompt mentions the legacy museum: " + item.key
                    for item in prompts
                    if re.search("半坡|banpo", item.content, re.I)
                ]
                return {
                    "status": "audited",
                    "museum_id": settings.EXPECTED_MUSEUM_ID,
                    "active_halls": [{"slug": item.slug, "name": item.name} for item in halls],
                    "active_exhibits": len(exhibits),
                    "exhibit_sources": sorted({item.source_name or "manual" for item in exhibits}),
                    "knowledge_documents": len(docs),
                    "indexed_documents": sum(doc.status == "completed" for doc in docs),
                    "search_chunks": (await es.client.count(index=es.index_name))["count"],
                    "users": (await session.execute(text("SELECT count(*) FROM users"))).scalar_one(),
                    "warnings": warnings,
                }
    finally:
        await es.close()
        await engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate", help="Offline validation; never connects to services")
    validate.add_argument("package", type=Path)
    environment = commands.add_parser("create-env", help="Generate NEW independent Compose deployment credentials")
    environment.add_argument("package", type=Path)
    environment.add_argument("--output", type=Path, required=True)
    environment.add_argument("--port", type=int, default=8081)
    environment.add_argument("--llm-model", default="qwen2.5:7b")
    environment.add_argument("--embedding-model", default="nomic-embed-text")
    environment.add_argument("--embedding-dims", type=int, default=768)
    initialize = commands.add_parser(
        "initialize", help="Initialize or resume a NEW database; never overwrite an old museum"
    )
    initialize.add_argument("package", type=Path)
    initialize.add_argument("--admin-email", required=True)
    initialize.add_argument("--env-file", type=Path)
    audit = commands.add_parser("audit", help="Read installation identity and active sources")
    audit.add_argument("--env-file", type=Path)
    args = parser.parse_args()
    from loguru import logger

    logger.remove()  # Bootstrap CLI reports safe structured output only.
    try:
        if args.command in {"validate", "create-env"}:
            package = load_package(args.package)
            if args.command == "validate":
                result = {
                    "status": "validated",
                    "museum_id": package.manifest.museum_id,
                    "package_sha256": package.digest,
                    "halls": len(package.dataset.halls),
                    "exhibits": len(package.dataset.exhibits),
                    "knowledge_files": len(package.contents),
                }
            else:
                if not 1024 <= args.port <= 65535 or not all(
                    re.fullmatch(r"[a-zA-Z0-9_.:/-]+", value) for value in [args.llm_model, args.embedding_model]
                ):
                    raise PackageError("Use a port between 1024 and 65535 and valid model names")
                result = create_environment(
                    package,
                    args.output,
                    port=args.port,
                    llm_model=args.llm_model,
                    embedding_model=args.embedding_model,
                    dims=args.embedding_dims,
                )
        else:
            settings = Settings(_env_file=args.env_file)  # No implicit fallback to this checkout's .env.
            result = asyncio.run(operate(args, settings))
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except PackageError as exc:
        print(json.dumps({"status": "refused", "error": str(exc)}, ensure_ascii=False))
        raise SystemExit(2) from None
    except MuseumDataValidationError as exc:
        print(json.dumps({"status": "invalid", "issues": exc.issues}, ensure_ascii=False))
        raise SystemExit(2) from None
    except ValidationError as exc:
        print(
            json.dumps({"status": "invalid", "fields": [list(err["loc"]) for err in exc.errors()]}, ensure_ascii=False)
        )
        raise SystemExit(2) from None
    except Exception as exc:
        # SQL/HTTP exceptions often embed credentials. Never print their repr.
        print(
            json.dumps(
                {
                    "status": "failed",
                    "error_type": type(exc).__name__,
                    "hint": "Check package files, migrations, services and model settings; then retry the same package",
                }
            )
        )
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
