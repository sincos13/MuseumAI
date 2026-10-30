"""Hall syntax and identity resolution against the museum's actual catalog."""

import re
from collections.abc import Iterable, Mapping
from typing import Any


def temporary_hall_description(
    base_description: str | None = None,
    exhibit_names: list[str] | None = None,
    *,
    exhibit_count: int | None = None,
) -> str:
    """Build the shared temporary-hall copy from currently active exhibits."""
    base = str(base_description or "").strip()
    names: list[str] = []
    seen: set[str] = set()
    for raw_name in exhibit_names or []:
        name = str(raw_name or "").strip()
        if name and name not in seen:
            seen.add(name)
            names.append(name)

    count = max(int(exhibit_count or 0), len(names))
    if count <= 0:
        status = "当前暂无已发布展品信息。"
        return f"{base} {status}".strip()

    summary = f"当前已发布 {count} 件展品。"
    if names:
        summary += f" 当前展品包括：{'、'.join(names[:3])}。"
    return f"{base} {summary}".strip()


def normalize_hall(value: str | None) -> str | None:
    """Normalize slug syntax; this does not prove that a hall exists."""
    if not isinstance(value, str):
        return None
    slug = value.strip().lower()
    if len(slug) <= 100 and re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        return slug
    return None


def _field(hall: Any, key: str, default: Any = None) -> Any:
    return hall.get(key, default) if isinstance(hall, Mapping) else getattr(hall, key, default)


def normalize_hall_aliases(values: Any) -> list[str]:
    """Validate aliases with the same constraints for admin and file import."""
    if not isinstance(values, list) or len(values) > 30:
        raise ValueError("aliases must be a list of at most 30 strings")
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not isinstance(value, str) or not value.strip() or len(value.strip()) > 255:
            raise ValueError("each hall alias must be a nonempty string of at most 255 characters")
        alias = value.strip()
        if alias.casefold() not in seen:
            seen.add(alias.casefold())
            result.append(alias)
    return result


def hall_identity_keys(hall: Any) -> set[str]:
    return {
        str(value).strip().casefold()
        for value in [_field(hall, "slug"), _field(hall, "name"), *(_field(hall, "aliases", []) or [])]
        if value and str(value).strip()
    }


def hall_identity_conflicts(halls: Iterable[Any]) -> list[str]:
    owners: dict[str, str] = {}
    issues: list[str] = []
    for hall in halls:
        slug = str(_field(hall, "slug"))
        for key in sorted(hall_identity_keys(hall)):
            owner = owners.setdefault(key, slug)
            if owner != slug:
                issues.append(f"hall identity '{key}' is shared by '{owner}' and '{slug}'")
    return issues


def resolve_hall_slug(value: str | None, halls: Iterable[Any]) -> str | None:
    """Resolve slug, display name or alias; unknown and ambiguous inputs fail closed."""
    if not isinstance(value, str) or not value.strip():
        return None
    key = value.strip().casefold()
    candidates = {
        slug for hall in halls
        if key in hall_identity_keys(hall) and (slug := normalize_hall(_field(hall, "slug")))
    }
    return next(iter(candidates)) if len(candidates) == 1 else None


def normalize_halls(values: list[str] | None) -> list[str]:
    return list(dict.fromkeys(slug for value in values or [] if (slug := normalize_hall(value))))


def is_canonical_hall(value: str | None, halls: Iterable[Any] = ()) -> bool:
    return resolve_hall_slug(value, halls) is not None


def is_temporary_hall(value: str | None, halls: Iterable[Any] = ()) -> bool:
    records = list(halls)
    slug = resolve_hall_slug(value, records)
    return bool(slug and any(_field(hall, "slug") == slug and _field(hall, "is_temporary", False) for hall in records))


def hall_display_name(value: str | None, halls: Iterable[Any] = ()) -> str:
    records = list(halls)
    slug = resolve_hall_slug(value, records)
    for hall in records:
        if slug and _field(hall, "slug") == slug:
            return str(_field(hall, "name") or slug)
    return str(value or "").strip()
