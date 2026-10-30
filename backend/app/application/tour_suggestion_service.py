"""Deterministic, visitor-friendly suggestion questions for the mini-program."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence

from app.domain.suggestion_config import SuggestionConfig

_DEFAULT_POLICY = SuggestionConfig()

SUGGESTION_MIN_LENGTH = 8
SUGGESTION_PREFERRED_MAX_LENGTH = 16
SUGGESTION_MAX_LENGTH = 18

SUGGESTION_META_FRAGMENTS = (
    "测试数据",
    "这是一条测试",
    "真实数据",
    "馆方数据",
    "数据接入",
    "上线后",
    "后续上线",
    "如何替换",
    "怎么替换",
    "导入数据",
    "上传数据",
)
SUGGESTION_JARGON_FRAGMENTS = (
    "层位",
    "形制",
    "证据链",
    "对应关系",
    "可核对",
    "剖面",
    "夯实",
    "烧结",
    "差序",
    "同心磨痕",
    "判断型",
    "合理推断",
    "直接观察",
    "现场信息",
)
SUGGESTION_GENERIC_COPY = {
    "这里有哪些可以直接观察的证据",
    "哪些结论仍需要保留不确定性",
    "最值得记录的观察点是什么",
    "我可以怎样整理这段参观笔记",
    "这些材料反映了怎样的史前生活",
    "它与更大的历史问题有什么联系",
    "可以从哪些材料和制作痕迹观察",
    "这些细节可能对应什么用途",
    "这个展厅的核心主题是什么",
    "这里最值得看什么",
    "这个展厅讲什么",
}
SUGGESTION_VAGUE_PATTERNS = (
    r"^(?:眼前|这里|这些|这个|这件|这座|它)",
    r"^(?:为什么|怎么|怎样|如何|哪些|有什么|有何)",
    r".*(?:怎样|怎么|如何)理解",
    r".*(?:值得|应该).*(?:看|观察|记录).*什么",
    r".*(?:还有|接下来).*(?:问|了解)什么",
)


SUBJECT_NAME_NOISE_FRAGMENTS = (
    "测试",
    "占位",
    "待替换",
    "待补充",
    "临时数据",
    "示例",
    "样例",
    "模拟",
    "虚拟",
    "示例名称",
    "维护用",
    "数据接入",
)
SUBJECT_ASCII_NOISE_LABELS = ("demo", "test")
SUBJECT_PLACEHOLDER_LABELS = (
    "临时数据",
    "测试数据",
    "示例名称",
    "数据接入",
    "待替换",
    "待补充",
    "维护用",
    "测试",
    "占位",
    "示例",
    "样例",
    "模拟",
    "虚拟",
    "demo",
    "test",
)


def normalize_suggestion(value: object) -> str:
    question = re.sub(r"\s+", " ", str(value or "")).strip()
    if question.endswith("?"):
        question = f"{question[:-1]}？"
    return question


def suggestion_rejection_reason(value: object, *, policy: SuggestionConfig | None = None) -> str | None:
    question = normalize_suggestion(value)
    normalized = question.rstrip("？?。！! ")
    if len(question) < SUGGESTION_MIN_LENGTH:
        return f"must contain at least {SUGGESTION_MIN_LENGTH} characters"
    if len(question) > SUGGESTION_MAX_LENGTH:
        return f"exceeds {SUGGESTION_MAX_LENGTH} characters"
    if not question.endswith("？"):
        return "must end with a question mark"
    if any(fragment in question for fragment in SUGGESTION_META_FRAGMENTS):
        return "contains maintenance or test-data wording"
    if any(fragment in question for fragment in SUGGESTION_JARGON_FRAGMENTS):
        return "contains unexplained specialist wording"
    if normalized in SUGGESTION_GENERIC_COPY:
        return "is a generic placeholder"
    if any(re.search(pattern, normalized) for pattern in SUGGESTION_VAGUE_PATTERNS):
        return "does not name a concrete exhibit or feature"
    return None


def is_meaningful_suggestion(value: object, *, policy: SuggestionConfig | None = None) -> bool:
    return suggestion_rejection_reason(value, policy=policy) is None


def quality_suggestions(values: object, *, limit: int = 6, policy: SuggestionConfig | None = None) -> list[str]:
    if not isinstance(values, (list, tuple)):
        return []
    suggestions: list[str] = []
    seen: set[str] = set()
    for value in values:
        question = normalize_suggestion(value)
        if not is_meaningful_suggestion(question, policy=policy) or question in seen:
            continue
        seen.add(question)
        suggestions.append(question)
        if len(suggestions) >= limit:
            break
    return suggestions


def _strip_subject_noise(value: str, policy: SuggestionConfig) -> str:
    subject = value.strip(" ，、。:：—–-·/|｜")
    changed = True
    while changed and subject:
        changed = False
        for prefix in policy.subject_noise_prefixes:
            if subject.startswith(prefix):
                subject = subject[len(prefix) :]
                changed = True
        for suffix in policy.subject_noise_suffixes:
            if subject.endswith(suffix):
                subject = subject[: -len(suffix)]
                changed = True
        subject = subject.strip(" ，、。:：—–-·/|｜")
    return subject


def _bounded_name_subject(value: str, policy: SuggestionConfig) -> str:
    subject = _strip_subject_noise(value, policy)
    subject = re.sub(r"^(?:这个|那个|这些|眼前|这里)", "", subject)
    for fragment in (*SUGGESTION_META_FRAGMENTS, *SUGGESTION_JARGON_FRAGMENTS):
        subject = subject.replace(fragment, "")
    subject = _strip_subject_noise(subject, policy)
    if 2 <= len(subject) <= 8:
        return subject

    for ending in policy.subject_object_endings:
        position = subject.rfind(ending)
        if position < 0:
            continue
        remaining = subject[:position]
        modifiers: list[str] = []
        available = 8 - len(ending)
        while available > 0:
            matches = [
                term for term in policy.subject_modifier_terms if len(term) <= available and remaining.endswith(term)
            ]
            if not matches:
                break
            term = max(matches, key=len)
            modifiers.insert(0, term)
            remaining = remaining[: -len(term)]
            available -= len(term)
        candidate = f"{''.join(modifiers)}{ending}"
        if 2 <= len(candidate) <= 8:
            return candidate

    candidate = subject[-8:].lstrip("的之与和及")
    if 2 <= len(candidate) <= 8:
        return candidate
    return ""


def _extract_special_subject(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    tomb_fragment = re.search(r"(\d{1,4}号墓).{0,10}?(残片|碎片|陶片|骨片)", normalized)
    if tomb_fragment:
        return f"{tomb_fragment.group(1)}{tomb_fragment.group(2)}"
    if re.search(r"出土.{0,4}?(残片|碎片|陶片|骨片)", normalized):
        fragment = re.search(r"(残片|碎片|陶片|骨片)", normalized)
        if fragment:
            return f"出土{fragment.group(1)}"
    inventory = re.search(
        r"(?:馆藏)?编号[:：]?([A-Za-z]{1,8}(?:[-_:][A-Za-z0-9]+)+)",
        normalized,
        flags=re.IGNORECASE,
    )
    if inventory and len(inventory.group(1)) <= 14:
        return inventory.group(1)
    return ""


def _strip_standardized_placeholder_labels(value: str | None) -> str:
    normalized = unicodedata.normalize("NFKC", str(value or "")).strip()
    labels = "|".join(re.escape(label) for label in sorted(SUBJECT_PLACEHOLDER_LABELS, key=len, reverse=True))
    bracketed = re.compile(
        rf"^\s*(?:【\s*(?:{labels})\s*】|"
        rf"\[\s*(?:{labels})\s*\]|"
        rf"\(\s*(?:{labels})\s*\))\s*",
        flags=re.IGNORECASE,
    )
    delimited = re.compile(
        rf"^\s*(?:{labels})\s*(?:[:：/_|｜·—–-]+|\s+)\s*",
        flags=re.IGNORECASE,
    )
    while normalized:
        stripped = bracketed.sub("", normalized, count=1)
        if stripped == normalized:
            stripped = delimited.sub("", normalized, count=1)
        if stripped == normalized:
            break
        normalized = stripped.strip()
    return normalized


def _has_subject_name_noise(value: str | None) -> bool:
    normalized = _strip_standardized_placeholder_labels(value)
    # A leading bracketed dataset label is presentation metadata and may be
    # removed. Noise remaining in the actual name must never become a question.
    normalized = re.sub(
        r"^(?:(?:【[^】]{1,40}】)|(?:\[[^\]]{1,40}\])|(?:\([^)]{1,40}\)))+",
        "",
        normalized,
    ).lower()
    if any(fragment in normalized for fragment in SUBJECT_NAME_NOISE_FRAGMENTS):
        return True
    return any(re.search(rf"(?<![a-z0-9]){label}(?![a-z0-9])", normalized) for label in SUBJECT_ASCII_NOISE_LABELS)


def _clean_subject(value: str | None, category: str | None, policy: SuggestionConfig) -> str:
    original = re.sub(
        r"\s+",
        "",
        _strip_standardized_placeholder_labels(value),
    )
    if special_subject := _extract_special_subject(original):
        return special_subject
    without_brackets = re.sub(
        r"(?:【[^】]{1,40}】|\[[^\]]{1,40}\])",
        "",
        original,
    )
    original = without_brackets or original.replace("【", "").replace("】", "")
    original = re.sub(r"[（(].*?[）)]", "", original).strip(" ，、。")
    parts = [part for part in re.split(r"[、，,:：/|｜·—–-]+", original) if _strip_subject_noise(part, policy)]
    ranked_parts = sorted(
        enumerate(parts),
        key=lambda item: (
            -int(any(ending in item[1] for ending in policy.subject_object_endings)),
            -int(2 <= len(_strip_subject_noise(item[1], policy)) <= 8),
            item[0],
        ),
    )
    for _, part in ranked_parts:
        if subject := _bounded_name_subject(part, policy):
            return subject

    category_value = _strip_standardized_placeholder_labels(category)
    if _has_subject_name_noise(category):
        category_value = ""
    category_text = _bounded_name_subject(re.sub(r"\s+", "", category_value), policy)
    if 2 <= len(category_text) <= 6:
        return category_text
    return ""


def _description_anchors(description: str | None, *, limit: int = 3, policy: SuggestionConfig) -> list[str]:
    text = str(description or "")
    matches = sorted(
        (text.find(source), order, plain)
        for order, (source, plain) in enumerate(policy.description_anchors)
        if source in text
    )
    anchors: list[str] = []
    for _, _, plain in matches:
        if plain not in anchors:
            anchors.append(plain)
        if len(anchors) >= limit:
            break
    return anchors


def _ordered_short_candidates(candidates: Sequence[str]) -> list[str]:
    accepted = quality_suggestions(list(candidates), limit=len(candidates))
    preferred = [question for question in accepted if len(question) <= SUGGESTION_PREFERRED_MAX_LENGTH]
    longer = [question for question in accepted if question not in preferred]
    return [*preferred, *longer]


def _anchor_questions(anchor: str, policy: SuggestionConfig) -> list[str]:
    if any(marker in anchor for marker in policy.anchor_mark_markers):
        group = "anchor_mark"
    elif anchor.endswith(tuple(policy.anchor_pattern_endings)):
        group = "anchor_pattern"
    elif any(marker in anchor for marker in policy.anchor_trace_markers):
        group = "anchor_trace"
    else:
        group = "anchor_default"
    return [template.format(anchor=anchor) for template in policy.question_templates[group]]


def _subject_questions(subject: str, policy: SuggestionConfig) -> list[str]:
    if any(marker in subject for marker in policy.fragment_subject_markers):
        group = "fragment"
    elif any(marker in subject for marker in policy.display_subject_markers):
        group = "display"
    elif any(marker in subject for marker in policy.site_subject_markers):
        group = "site"
    elif any(subject.endswith(marker) for marker in policy.kiln_subject_markers):
        group = "kiln"
    elif any(subject.endswith(marker) for marker in policy.tool_or_artifact_markers):
        group = "artifact"
    elif re.fullmatch(r"[A-Za-z0-9]+(?:[-_:][A-Za-z0-9]+)+", subject):
        group = "inventory"
    else:
        group = "default"
    return [template.format(subject=subject) for template in policy.question_templates[group]]


def derive_exhibit_suggestions(
    name: str | None,
    description: str | None,
    category: str | None = None,
    *,
    policy: SuggestionConfig | None = None,
) -> list[str]:
    """Build two short questions solely from trusted exhibit fields."""
    policy = policy or _DEFAULT_POLICY
    if _has_subject_name_noise(name):
        return []
    subject = _clean_subject(name, category, policy)
    anchor_limit = 3 if subject else len(policy.description_anchors)
    anchors = _description_anchors(description, limit=anchor_limit, policy=policy)
    subject_from_anchor = False
    if not subject:
        anchors = [anchor for anchor in anchors if anchor in policy.strong_detail_anchors][:3]
    if not subject and anchors:
        subject = anchors[0]
        subject_from_anchor = True
    if not subject:
        return []

    if subject_from_anchor:
        candidates = [question for anchor in anchors for question in _anchor_questions(anchor, policy)]
    else:
        subject_questions = _subject_questions(subject, policy)
        candidates = [subject_questions[0]]
        candidates.extend(
            question
            for anchor in anchors
            if anchor in policy.strong_detail_anchors
            for question in _anchor_questions(anchor, policy)
        )
        candidates.extend(subject_questions[1:])
    return _ordered_short_candidates(candidates)[:2]
