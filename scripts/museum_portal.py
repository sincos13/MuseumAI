#!/usr/bin/env python3
"""Create server configuration or provision an empty museum import portal."""
import argparse
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))

from app.application.museum_package import PackageError
from app.application.museum_portal_service import provision_empty_portal
from app.config.settings import Settings
from app.infra.postgres.models import MuseumInstallation
from museum_instance import create_environment, new_admin_password_hash
from pydantic import TypeAdapter
from pydantic.networks import EmailStr
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine


async def initialize(email):
    settings = Settings()
    if not settings.MUSEUM_SELF_SERVICE_IMPORT:
        raise PackageError("MUSEUM_SELF_SERVICE_IMPORT must be true")
    email = str(TypeAdapter(EmailStr).validate_python(email))
    engine = create_async_engine(settings.DATABASE_URL)
    try:
        async with engine.connect() as connection:
            locked = (await connection.execute(text("SELECT pg_try_advisory_lock(682417236)"))).scalar_one()
            await connection.commit()
            if not locked:
                raise PackageError("Another initializer is running")
            try:
                async with AsyncSession(connection, expire_on_commit=False) as session:
                    existing = await session.get(MuseumInstallation, 1)
                    if existing:
                        if existing.search_index != settings.ELASTICSEARCH_INDEX:
                            raise PackageError("Portal database/index identity mismatch")
                        return {"status": "already_prepared", "museum_status": existing.status}
                    password_hash = new_admin_password_hash()
                    await provision_empty_portal(session, search_index=settings.ELASTICSEARCH_INDEX,
                        email=email, password_hash=password_hash)
                    await session.commit()
                    return {"status": "awaiting_import", "admin_email": email, "next": "/admin/import"}
            finally:
                await connection.rollback()
                await connection.execute(text("SELECT pg_advisory_unlock(682417236)"))
                await connection.commit()
    finally:
        await engine.dispose()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    create = commands.add_parser("create-env")
    create.add_argument("--output", type=Path, required=True)
    create.add_argument("--port", type=int, default=8081)
    create.add_argument("--llm-model", default="qwen2.5:7b")
    create.add_argument("--embedding-model", default="nomic-embed-text")
    create.add_argument("--dims", type=int, default=768)
    init = commands.add_parser("initialize")
    init.add_argument("--admin-email", required=True)
    args = parser.parse_args()
    try:
        if args.command == "create-env":
            result = create_environment(None, args.output, port=args.port, llm_model=args.llm_model,
                embedding_model=args.embedding_model, dims=args.dims, self_service=True)
            result["museum_id"] = None
            result["note"] = "Empty portal: configure model access, start services, then upload in /admin/import"
        else:
            result = asyncio.run(initialize(args.admin_email))
        print(json.dumps(result, ensure_ascii=False))
    except PackageError as exc:
        print(json.dumps({"status": "refused", "error": str(exc)}, ensure_ascii=False))
        raise SystemExit(2) from None
    except Exception as exc:
        print(json.dumps({"status": "failed", "error_type": type(exc).__name__,
            "hint": "Check migrations, database access and model configuration"}))
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
