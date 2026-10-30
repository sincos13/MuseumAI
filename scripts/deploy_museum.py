#!/usr/bin/env python3
"""Deploy one museum with isolated Docker Compose services and persistent volumes."""

import argparse
import getpass
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["start", "status", "stop", "audit", "logs"])
    parser.add_argument("--instance", type=Path, required=True)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--package", type=Path)
    source.add_argument("--portal", action="store_true", help="Start empty; the curator uploads museum content in the browser")
    parser.add_argument("--admin-email", default="curator@museum.example.com")
    args = parser.parse_args()
    instance = args.instance.resolve()
    package = args.package.resolve() if args.package else ROOT / "data/museum_template"
    if not (instance / "app.env").is_file() or not (instance / "instance.env").is_file():
        parser.error("Generate a new instance with museum_instance.py create-env first")
    env = dict(os.environ, MUSEUM_INSTANCE_DIR=instance.as_posix(), MUSEUM_PACKAGE_DIR=package.as_posix())
    command = [
        "docker",
        "compose",
        "--env-file",
        str(instance / "instance.env"),
        "-f",
        str(ROOT / "deploy/standalone/compose.yml"),
    ]

    def run(*arguments):
        subprocess.run([*command, *arguments], env=env, cwd=ROOT, check=True)

    try:
        if args.action == "start":
            # Offline validation comes before downloads or infrastructure mutation.
            if not args.portal:
                subprocess.run(
                    [sys.executable, str(ROOT / "scripts/museum_instance.py"), "validate", str(package)], check=True
                )
            run("build")
            run("--profile", "tools", "build", "operator")
            run("up", "-d", "--wait", "postgres", "redis", "elasticsearch")
            run("run", "--rm", "operator", "python", "-m", "alembic", "upgrade", "head")
            env["MUSEAI_ADMIN_PASSWORD"] = os.environ.get("MUSEAI_ADMIN_PASSWORD") or getpass.getpass(
                "Museum admin password: "
            )
            try:
                initialize = ["scripts/museum_portal.py", "initialize"] if args.portal else [
                    "scripts/museum_instance.py", "initialize", "/museum-package",
                ]
                run("run", "--rm", "operator", "python", *initialize, "--admin-email", args.admin_email)
            finally:
                env.pop("MUSEAI_ADMIN_PASSWORD", None)
            run("up", "-d", "--wait", "backend", "frontend")
            run("ps")
            print("PORTAL_READY: log in at /admin/import and upload your ZIP package" if args.portal else
                "MUSEUM_READY: open the visitor_url returned by create-env; manage knowledge in /admin/documents")
        elif args.action == "audit":
            run("run", "--rm", "operator", "python", "scripts/museum_instance.py", "audit")
        elif args.action == "stop":
            run("stop")  # Never delete volumes or data.
        elif args.action == "logs":
            run("logs", "--tail", "100", "backend", "frontend")
        else:
            run("ps")
    except subprocess.CalledProcessError:
        print(
            "Deployment stopped at a failed command. Correct the error and retry; data volumes remain."
        )
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
