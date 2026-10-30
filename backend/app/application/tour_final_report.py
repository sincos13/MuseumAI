"""Final visitor-facing report: cover / interests / knowledge cards / profile.

Identity-agnostic by design: the report is assembled from the visitor's own
route, words and behaviour. The guide persona appears only as a small stamp on
the cover, so the same engine works for any museum and any number of personas.

Sections:
- cover      deterministic (route strip, basic counts, persona stamp)
- interests  deterministic (BM25 over knowledge docs -> story/background/links)
- cards      LLM-generated, ground-anchored, with a rules fallback
- profile    rules-derived archetype + LLM-written affirmation
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from datetime import UTC
from typing import Any

from loguru import logger
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.hall_normalizer import normalize_hall
from app.application.museum_profile_service import get_session_museum_configuration
from app.application.tour_event_service import get_events_by_session
from app.application.tour_guide_service import entity_id
from app.application.tour_personal_report import collect_records
from app.application.tour_session_service import get_session
from app.infra.postgres.models import Document, Exhibit, TourReportModel, TourSessionModel

VERSION = 1

FORBIDDEN_PHRASES = ("你学会了", "你已经", "你掌握了", "深刻理解", "学习能力")

WHY_MARKERS = ("为什么", "为何", "怎么会", "何故")
MAINTENANCE_MARKERS = ("修", "维护", "清淤", "清理", "渠", "换", "制度", "轮值")
MATERIAL_MARKERS = ("材料", "结构", "纹", "痕", "口沿", "接口", "质地", "工艺", "制作", "形制")
HYPOTHESIS_MARKERS = ("我觉得", "可能", "是不是", "大概", "也许", "感觉", "猜想")


def _norm(value: Any) -> str:
    return unicodedata.normalize("NFKC", str(value or "")).strip().lower()


def _unique(seq) -> list:
    out: list = []
    seen: set = set()
    for item in seq:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def _clean_label(title: str) -> str:
    # Strip leading file codes such as "T01 ", "JH-002 ", "K00-world " or "H01 ".
    label = re.sub(r"^[A-Za-z0-9][A-Za-z0-9_\-\.]*[\s_\-—–]+", "", str(title or "").strip())
    return label or str(title or "").strip()


_METADATA_LINE = re.compile(
    r"^(?:名称|别名|展厅|类别|年代|材质|尺寸|编号|展品名称|所在展厅)[：:]"
)


def _readable_paragraphs(text: str) -> list[str]:
    """Turn raw knowledge text into readable paragraphs.

    Drops Markdown headings and catalog metadata lines (``名称：…；尺寸：…``)
    so the report shows narrative prose instead of catalog scaffolding.
    """
    without_headings = re.sub(r"^#{1,6}\s*.*$", "", str(text or ""), flags=re.M)
    paragraphs: list[str] = []
    for part in re.split(r"\n\s*\n", without_headings):
        clean = re.sub(r"\s+", " ", part).strip()
        if not clean or _METADATA_LINE.match(clean):
            continue
        if len(clean) < 12:
            continue
        paragraphs.append(clean)
    return paragraphs


def _readable_paragraph(text: str) -> str:
    paragraphs = _readable_paragraphs(text)
    return paragraphs[0] if paragraphs else ""


def _numbers_allowed(text: str, allowed: str) -> bool:
    """Every digit sequence in ``text`` must already appear in ``allowed``."""
    return all(number in allowed for number in re.findall(r"\d+", str(text or "")))


_UNIT_AFTER_NUMBER = re.compile(
    r"\d+\s*(?:厘米|毫米|英寸|英尺|毫升|升|千克|公斤|克|斤|米)"
)


def _units_allowed(text: str, allowed: str) -> bool:
    """A rewritten number must keep its original measure unit (48厘米 != 48英寸)."""
    compact_allowed = re.sub(r"\s+", "", str(allowed or ""))
    for match in _UNIT_AFTER_NUMBER.finditer(str(text or "")):
        if re.sub(r"\s+", "", match.group(0)) not in compact_allowed:
            return False
    return True


# ---------------------------------------------------------------------------
# Cover (deterministic)
# ---------------------------------------------------------------------------

def _ordered_halls(events) -> list[str]:
    return _unique(
        normalize_hall(e.hall)
        for e in sorted(events, key=lambda x: x.created_at)
        if normalize_hall(e.hall)
    )


def _hall_exhibit_counts(events) -> dict[str, int]:
    counts: dict[str, set] = {}
    for e in events:
        if getattr(e, "event_type", None) == "exhibit_view" and getattr(e, "exhibit_id", None):
            slug = normalize_hall(getattr(e, "hall", None)) or ""
            counts.setdefault(slug, set()).add(entity_id(e.exhibit_id))
    return {slug: len(ids) for slug, ids in counts.items()}


def build_cover(session, events, museum, persona, hall_name_map) -> dict:
    started = getattr(session, "tour_started_at", None) or getattr(session, "started_at", None)
    completed = getattr(session, "completed_at", None)
    duration = 0.0
    if started is not None and completed is not None:
        try:
            duration = round(max(0.0, (completed - started).total_seconds() / 60.0), 1)
        except TypeError:
            duration = 0.0

    halls = _ordered_halls(events)
    counts = _hall_exhibit_counts(events)
    route = [
        {"hall": slug, "name": (hall_name_map or {}).get(slug, slug), "exhibits": counts.get(slug, 0)}
        for slug in halls
    ]
    questions = sum(1 for e in events if getattr(e, "event_type", None) == "exhibit_question")
    exhibits = len(
        {entity_id(e.exhibit_id) for e in events if getattr(e, "event_type", None) == "exhibit_view" and getattr(e, "exhibit_id", None)}
    )

    date = ""
    if completed is not None:
        try:
            from zoneinfo import ZoneInfo

            tz = getattr(museum, "timezone", "Asia/Shanghai") or "Asia/Shanghai"
            date = completed.astimezone(ZoneInfo(tz)).strftime("%Y-%m-%d")
        except Exception:
            date = completed.strftime("%Y-%m-%d")

    return {
        "museum_name": getattr(museum, "name", "") or "",
        "date": date,
        "persona": {"code": persona.code, "name": persona.name, "icon": persona.icon},
        "duration_minutes": duration,
        "questions": questions,
        "exhibits": exhibits,
        "halls": len(halls),
        "route": route,
    }


# ---------------------------------------------------------------------------
# Signals + archetype (deterministic)
# ---------------------------------------------------------------------------

def _rate(questions, markers) -> float:
    if not questions:
        return 0.0
    return sum(1 for q in questions if any(m in q for m in markers)) / len(questions)


def derive_signals(turns, events) -> dict:
    questions = [t["question"] for t in turns]
    exhibits = len(
        {entity_id(e.exhibit_id) for e in events if getattr(e, "event_type", None) == "exhibit_view" and getattr(e, "exhibit_id", None)}
    )
    subjects = len({t.get("exhibit_id") or t.get("subject") or "x" for t in turns})
    return {
        "questions": len(questions),
        "exhibits": exhibits,
        "halls": len(_ordered_halls(events)),
        "subjects": max(1, subjects),
        "depth": round(len(questions) / max(1, subjects), 2),
        "why_rate": _rate(questions, WHY_MARKERS),
        "material_rate": _rate(questions, MATERIAL_MARKERS),
        "hypothesis_rate": _rate(questions, HYPOTHESIS_MARKERS),
        "maintenance": any(any(m in q for m in MAINTENANCE_MARKERS) for q in questions),
    }


def classify_archetype(signals) -> tuple[str, str]:
    if signals["questions"] <= 1:
        return ("listener", "听讲型观众")
    if signals["maintenance"]:
        return ("maintenance", "维护派观察者")
    if signals["material_rate"] >= 0.4:
        return ("detail", "细节派观察者")
    if signals["why_rate"] >= 0.5:
        return ("inquiry", "追问型观众")
    if signals["halls"] >= 3 and signals["exhibits"] >= 4:
        return ("survey", "广览型观众")
    return ("curious", "好奇的观众")


# ---------------------------------------------------------------------------
# Interests (deterministic: BM25 over knowledge docs -> story/background/links)
# ---------------------------------------------------------------------------

async def derive_interests(es_client, turns, session) -> list[dict]:
    questions = [t["question"] for t in turns if len(t["question"].strip()) >= 2]
    if not questions or es_client is None:
        return []

    hits_by_doc: dict[str, dict] = {}
    try:
        for q in questions:
            for hit in await es_client.search_bm25(q, top_k=5, source_types=["document"]):
                sid = str(hit.get("source_id") or "")
                if not sid:
                    continue
                entry = hits_by_doc.setdefault(sid, {"chunks": [], "questions": []})
                entry["chunks"].append(hit)
                if q not in entry["questions"]:
                    entry["questions"].append(q)
    except Exception as exc:
        logger.warning("Final report interest retrieval failed: {}", type(exc).__name__)
        return []

    if not hits_by_doc:
        return []

    ranked = sorted(hits_by_doc.items(), key=lambda kv: len(kv[1]["questions"]), reverse=True)[:2]
    ids = [sid for sid, _ in ranked]

    docs: dict[str, Document] = {}
    try:
        rows = (await session.execute(select(Document).where(Document.id.in_(ids)))).scalars().all()
        docs = {r.id: r for r in rows}
    except Exception as exc:
        logger.warning("Final report reading-link lookup failed: {}", type(exc).__name__)

    interests: list[dict] = []
    for sid, entry in ranked:
        chunks = entry["chunks"]
        meta = (chunks[0].get("metadata") or {}) if chunks else {}
        title = str(meta.get("title") or meta.get("name") or sid)
        label = _clean_label(title)
        doc = docs.get(sid)
        content = getattr(doc, "content_text", "") if doc is not None else ""
        if content:
            paragraphs = _readable_paragraphs(content)
            story = paragraphs[0][:400] if paragraphs else ""
            background = paragraphs[1][:300] if len(paragraphs) > 1 else ""
        else:
            level1 = sorted(
                [c for c in chunks if (c.get("chunk_level") or 0) == 1],
                key=lambda c: len(c.get("content") or ""),
                reverse=True,
            )
            if not level1:
                level1 = sorted(chunks, key=lambda c: len(c.get("content") or ""), reverse=True)
            story = _readable_paragraph(level1[0].get("content") or "")[:400] if level1 else ""
            background = _readable_paragraph(level1[1].get("content") or "")[:300] if len(level1) > 1 else ""

        reading: list[dict] = []
        if doc is not None and getattr(doc, "source_url", ""):
            reading.append({
                "title": getattr(doc, "title", "") or label,
                "url": doc.source_url,
                "source_label": getattr(doc, "source_label", "") or "馆方资料",
            })

        interests.append({
            "dimension": label,
            "evidence_questions": list(entry["questions"])[:3],
            "story": story,
            "background": background,
            "reading": reading,
            "sources": [{"id": sid, "title": label, "snippet": story[:200]}],
        })
    return interests


# ---------------------------------------------------------------------------
# Interest polish (LLM rewrites the retrieved text in the guide's voice)
# ---------------------------------------------------------------------------

PERSONA_VOICE_LIMIT = 600


class InterestItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dimension: str
    story: str = Field(default="", max_length=400)
    background: str = Field(default="", max_length=300)


class InterestsPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[InterestItem] = Field(max_length=4)


def _interest_allowed(interest: dict) -> str:
    return " ".join([
        str(interest.get("story") or ""),
        str(interest.get("background") or ""),
        *[str((s or {}).get("snippet") or "") for s in (interest.get("sources") or [])],
    ])


async def _polish_interests_via_llm(interests, persona, provider) -> list[dict]:
    guide = getattr(persona, "guide", None)
    method = str(getattr(guide, "method", "") or "")
    voice = f"{getattr(persona, 'name', '')}。{getattr(persona, 'description', '')}。{method}"[:PERSONA_VOICE_LIMIT]
    payload = [
        {
            "dimension": i["dimension"],
            "story": i.get("story", ""),
            "background": i.get("background", ""),
            "sources": [str((s or {}).get("snippet") or "") for s in (i.get("sources") or [])[:1]],
        }
        for i in interests
    ]
    prompt = (
        f"你是博物馆导览「{getattr(persona, 'name', '')}」。你的讲述风格：{voice}\n"
        "下面列出游客本次关心的主题，以及馆方资料原文。请用你的身份口吻，把每个主题的 "
        '"story"（这段故事）和 "background"（背景补充）各润色成一段自然的话，不要写成模板标题。\n'
        "硬性规则：只能使用给出的资料内容，不得新增数字、年代、人名、地名、文献名或馆方不存在的展品；"
        '数字和单位必须与资料完全一致（资料写"厘米"就不要写成"英寸"）；'
        '不得写"你学会了"；不得改变事实；story <= 160 字，background <= 120 字。\n'
        '只返回 JSON：{"items":[{"dimension":"...","story":"...","background":"..."}]}'
    )
    kwargs = {}
    if getattr(provider, "supports_model_override", False) is True and getattr(provider, "report_model", None):
        kwargs["model"] = provider.report_model
    response = await provider.generate(
        [{"role": "system", "content": prompt}, {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
        **kwargs,
    )
    content = str(getattr(response, "content", response)).strip()
    content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content)
    data = InterestsPayload.model_validate_json(content)
    by_dimension = {item.dimension: item for item in data.items}
    polished: list[dict] = []
    for interest in interests:
        item = by_dimension.get(interest["dimension"])
        if item is None:
            polished.append(interest)
            continue
        allowed = _interest_allowed(interest)
        rewritten = item.story + item.background
        if not _numbers_allowed(rewritten, allowed) or not _units_allowed(rewritten, allowed):
            polished.append(interest)
            continue
        polished.append({
            **interest,
            "story": item.story or interest.get("story", ""),
            "background": item.background or interest.get("background", ""),
        })
    return polished


async def polish_interests(interests, persona, provider) -> list[dict]:
    if not interests or provider is None:
        return interests
    try:
        return await _polish_interests_via_llm(interests, persona, provider)
    except Exception as exc:
        logger.warning("Final report interest polish used fallback: {}", type(exc).__name__)
        return interests


# ---------------------------------------------------------------------------
# Knowledge cards (LLM + fallback)
# ---------------------------------------------------------------------------

class CardItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    turn_id: str
    title: str = Field(min_length=1, max_length=30)
    points: list[str] = Field(min_length=1, max_length=4)
    caveat: str = Field(default="", max_length=160)
    source_ids: list[str] = Field(default_factory=list, max_length=6)


class CardsPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    cards: list[CardItem] = Field(max_length=6)


class ProfilePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")
    summary: str = Field(min_length=1, max_length=240)


def _validate_card(card: CardItem, turn: dict) -> bool:
    text = card.title + " " + " ".join(card.points)
    if any(phrase in text for phrase in FORBIDDEN_PHRASES):
        return False
    numbers = re.findall(r"\d+", text)
    allowed = str(turn.get("answer") or "") + " " + " ".join(
        str((s or {}).get("snippet") or "") for s in (turn.get("sources") or [])
    )
    if any(n not in allowed for n in numbers):
        return False
    return True


def _self_check(card: CardItem) -> str:
    return f"合上卡片，你还记得「{card.title}」说的是什么吗？"


def _materialize_card(card: CardItem, turn: dict) -> dict:
    src_map = {str((s or {}).get("source_id") or (s or {}).get("id")): s for s in (turn.get("sources") or [])}
    sources = [
        {
            "id": sid,
            "title": (src_map.get(sid) or {}).get("title", ""),
            "snippet": ((src_map.get(sid) or {}).get("snippet") or "")[:200],
        }
        for sid in card.source_ids
        if sid in src_map
    ]
    return {
        "id": card.turn_id,
        "title": card.title,
        "points": [p.strip() for p in card.points if p.strip()],
        "caveat": card.caveat,
        "sources": sources,
        "self_check": _self_check(card),
    }


async def _cards_via_llm(turns, provider) -> list[dict]:
    payload = [
        {
            "turn_id": t["event_id"],
            "subject": t["subject"],
            "question": str(t.get("question") or "")[:200],
            "answer": str(t.get("answer") or "")[:500],
            "sources": [
                {
                    "id": str((s or {}).get("source_id") or (s or {}).get("id") or ""),
                    "title": (s or {}).get("title", ""),
                    "snippet": ((s or {}).get("snippet") or (s or {}).get("content") or "")[:300],
                }
                for s in (t.get("sources") or [])[:2]
            ],
        }
        for t in turns[:8]
    ]
    prompt = (
        "你是博物馆参观编辑。把下面每段问答整理成一张可复习的知识卡片。\n"
        "规则：title 是一个能记住的短语（<=12 字），不要写\"关于XX的说明\"；"
        "points 是 2-4 条核心知识点（每条 <=40 字），只能来自该段回答与来源，不得新增数字或专名；"
        "caveat 写资料没有说明的地方（没有就留空）；source_ids 列出所依据的来源 id。\n"
        "只返回符合 schema 的 JSON："
        + json.dumps(CardsPayload.model_json_schema(), ensure_ascii=False)
    )
    kwargs = {}
    if getattr(provider, "supports_model_override", False) is True and getattr(provider, "report_model", None):
        kwargs["model"] = provider.report_model
    response = await provider.generate(
        [{"role": "system", "content": prompt}, {"role": "user", "content": json.dumps(payload, ensure_ascii=False)}],
        **kwargs,
    )
    content = str(getattr(response, "content", response)).strip()
    content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content)
    data = CardsPayload.model_validate_json(content)
    turn_by_id = {t["event_id"]: t for t in turns}
    cards = []
    for card in data.cards:
        turn = turn_by_id.get(card.turn_id)
        if turn is None or not _validate_card(card, turn):
            continue
        cards.append(_materialize_card(card, turn))
    return cards


def _fallback_cards(turns) -> list[dict]:
    cards = []
    for t in turns[:5]:
        points = [s.strip() for s in re.split(r"[。；;]", str(t.get("answer") or "")) if s.strip()][:2]
        if not points:
            points = [str(t.get("answer") or "")[:60]]
        sources = [
            {
                "id": str((s or {}).get("source_id") or (s or {}).get("id") or ""),
                "title": (s or {}).get("title", ""),
                "snippet": ((s or {}).get("snippet") or "")[:200],
            }
            for s in (t.get("sources") or [])[:2]
        ]
        cards.append({
            "id": t["event_id"],
            "title": _clean_label(t.get("subject") or "")[:12] or "这一件",
            "points": [p.strip()[:60] for p in points],
            "caveat": "",
            "sources": sources,
            "self_check": "",
        })
    return cards


async def build_cards(turns, provider) -> list[dict]:
    if not turns:
        return []
    if provider is not None:
        try:
            cards = await _cards_via_llm(turns, provider)
            if cards:
                return cards
        except Exception as exc:
            logger.warning("Final report cards used fallback: {}", type(exc).__name__)
    return _fallback_cards(turns)


# ---------------------------------------------------------------------------
# Profile (rules archetype + LLM affirmation)
# ---------------------------------------------------------------------------

def _profile_evidence(turns, signals) -> list[str]:
    questions = [t["question"] for t in turns]
    if not questions:
        return []
    preferred = []
    if signals["maintenance"]:
        preferred = [q for q in questions if any(m in q for m in MAINTENANCE_MARKERS)]
    elif signals["material_rate"] >= 0.4:
        preferred = [q for q in questions if any(m in q for m in MATERIAL_MARKERS)]
    picked = (preferred or questions)[:3]
    return [q[:80] for q in picked]


async def _profile_via_llm(archetype_label, evidence, interests, provider) -> str:
    interest_txt = "、".join(i["dimension"] for i in interests) or "本次参观"
    prompt = (
        "你是博物馆导览，为游客写一句结束语。\n"
        f"游客的画像：{archetype_label}。\n"
        f"兴趣重点：{interest_txt}。\n"
        f"游客自己的原话：{json.dumps(evidence, ensure_ascii=False)}。\n"
        "要求：summary 用 2-3 句（<=120 字）具体地肯定游客本次的做法，只描述行为、不评价能力。"
        "只能依据上面给出的原话和兴趣重点，不得编造游客没有做过的具体动作、次数、地点、年代、"
        "人名或文献名；不得写任何数字；不得写\"你学会了/你很聪明\"。"
        "只返回 JSON：{\"summary\":\"...\"}"
    )
    kwargs = {}
    if getattr(provider, "supports_model_override", False) is True and getattr(provider, "report_model", None):
        kwargs["model"] = provider.report_model
    response = await provider.generate(
        [{"role": "system", "content": prompt}], **kwargs
    )
    content = str(getattr(response, "content", response)).strip()
    content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content)
    data = ProfilePayload.model_validate_json(content)
    return data.summary


def _next_suggestion(interests) -> str:
    if not interests:
        return ""
    return f"下次可以顺着「{interests[0]['dimension']}」再往下看，或从你留下的问题继续。"


def _fallback_profile(signals, archetype_code, archetype_label, interests, evidence) -> dict:
    interest_txt = "、".join(i["dimension"] for i in interests) or "本次参观"
    summary = f"你是{archetype_label}。这次你更关注{interest_txt}，并留下了自己的观察与追问。"
    return {
        "archetype": archetype_code,
        "label": archetype_label,
        "summary": summary,
        "next_suggestion": _next_suggestion(interests),
        "evidence": evidence,
    }


async def build_profile(signals, turns, interests, provider) -> dict:
    archetype_code, archetype_label = classify_archetype(signals)
    evidence = _profile_evidence(turns, signals)
    if provider is not None:
        try:
            summary = await _profile_via_llm(archetype_label, evidence, interests, provider)
            if _grounding_ok(summary, turns, interests):
                return {
                    "archetype": archetype_code,
                    "label": archetype_label,
                    "summary": summary,
                    "next_suggestion": _next_suggestion(interests),
                    "evidence": evidence,
                }
        except Exception as exc:
            logger.warning("Final report profile used fallback: {}", type(exc).__name__)
    return _fallback_profile(signals, archetype_code, archetype_label, interests, evidence)


def _grounding_ok(text: str, turns, interests) -> bool:
    """Reject generated profile text that introduces digits not present in the evidence."""
    allowed = " ".join(str(t.get("answer") or "") for t in turns) + " "
    allowed += " ".join(str(t.get("question") or "") for t in turns) + " "
    allowed += " ".join(
        (i.get("story") or "") + (i.get("background") or "")
        for i in interests
    )
    return _numbers_allowed(text, allowed) and _units_allowed(text, allowed)


# ---------------------------------------------------------------------------
# Orchestrator + caching
# ---------------------------------------------------------------------------

def _fingerprint(records, persona, tour) -> str:
    payload = {
        "version": VERSION,
        "records": records,
        "persona": getattr(persona, "code", ""),
        "end": str(getattr(tour, "completed_at", None)),
    }
    return hashlib.sha256(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode()
    ).hexdigest()


async def ensure_final_report(
    session: AsyncSession,
    session_id: str,
    llm_provider,
    es_client,
    hall_name_map: dict[str, str] | None,
) -> dict | None:
    configuration = await get_session_museum_configuration(session, session_id)
    museum = configuration.museum
    tour = await get_session(session, session_id)
    persona = next(p for p in museum.personas if p.code == tour.persona)
    events = await get_events_by_session(session, session_id)
    if not events:
        return None

    exhibit_ids = {entity_id(e.exhibit_id) for e in events if getattr(e, "exhibit_id", None)}
    exhibit_rows = (
        (await session.execute(select(Exhibit).where(Exhibit.id.in_(exhibit_ids), Exhibit.is_active.is_(True))))
        .scalars()
        .all()
    )
    names = {e.id: e.name for e in exhibit_rows}

    records = collect_records(events, hall_name_map or {}, names)
    turns = [
        r
        for r in records
        if r.get("kind") == "conversation"
        and r.get("action") not in {"hint", "explain"}
        and str(r.get("question") or "").strip()
    ]

    cover = build_cover(tour, events, museum, persona, hall_name_map or {})
    signals = derive_signals(turns, events)
    interests = await derive_interests(es_client, turns, session)

    digest = _fingerprint(records, persona, tour)
    stmt = select(TourReportModel).where(TourReportModel.tour_session_id == session_id)
    model = (await session.execute(stmt)).scalar_one_or_none()
    if model is None:
        return None
    if model.final_report_hash == digest and model.final_report:
        return model.final_report

    # Release the DB connection before any model call.
    session.expunge(model)
    await session.commit()

    interests = await polish_interests(interests, persona, llm_provider)
    cards = await build_cards(turns, llm_provider)
    profile = await build_profile(signals, turns, interests, llm_provider)
    result = {
        "version": VERSION,
        "cover": cover,
        "interests": interests,
        "cards": cards,
        "profile": profile,
        "meta": {"selection_method": "model" if llm_provider is not None else "rules"},
    }

    await session.execute(
        select(TourSessionModel.id).where(TourSessionModel.id == session_id).with_for_update()
    )
    model = (await session.execute(stmt.execution_options(populate_existing=True))).scalar_one()
    model.final_report = result
    model.final_report_hash = digest
    await session.commit()
    return result
