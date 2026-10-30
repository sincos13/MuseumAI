"""Bounded ZIP extraction for curator-uploaded standard museum packages."""
import stat
import zipfile
from pathlib import Path, PurePosixPath

from app.application.museum_package import PackageError, load_package

MAX_ARCHIVE_BYTES = 100 * 1024 * 1024
MAX_EXPANDED_BYTES = 250 * 1024 * 1024
MAX_MEMBERS = 2000


def extract_package(archive: Path, destination: Path):
    total = 0
    seen = set()
    with zipfile.ZipFile(archive) as package:
        members = package.infolist()
        if len(members) > MAX_MEMBERS:
            raise PackageError("资料包文件过多，最多 2000 个。")
        for item in members:
            name = item.filename
            path = PurePosixPath(name)
            if (
                "\\" in name or ":" in name or path.is_absolute()
                or any(part in {"..", "."} or part.endswith((" ", ".")) for part in path.parts)
                or any(part.split(".")[0].upper() in {"CON", "PRN", "AUX", "NUL", *[f"COM{i}" for i in range(10)], *[f"LPT{i}" for i in range(10)]} for part in path.parts)
                or stat.S_ISLNK(item.external_attr >> 16) or item.flag_bits & 1
            ):
                raise PackageError("资料包含不安全路径、链接或加密文件。")
            key = name.rstrip("/").casefold()
            if key in seen:
                raise PackageError("资料包包含重复路径。")
            seen.add(key)
            target = (destination / name).resolve()
            if not target.is_relative_to(destination.resolve()):
                raise PackageError("文件必须位于资料包目录内。")
            if item.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            total += item.file_size
            if total > MAX_EXPANDED_BYTES or item.file_size > 50 * 1024 * 1024:
                raise PackageError("资料包解压后超过大小限制。")
            target.parent.mkdir(parents=True, exist_ok=True)
            with package.open(item) as source, target.open("xb") as output:
                written = 0
                while chunk := source.read(1024 * 1024):
                    written += len(chunk)
                    if written > item.file_size:
                        raise PackageError("文件实际大小与资料包记录不一致。")
                    output.write(chunk)
    roots = [p.parent for p in destination.rglob("manifest.json")]
    if len(roots) != 1:
        raise PackageError("ZIP 内必须有且仅有一份 manifest.json。")
    return load_package(roots[0])
