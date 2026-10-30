"""Resolve curator-authored source IDs against the active museum catalog."""
from app.application.curator_service import build_structured_route


def build_visitor_route(tour_session, configuration, halls, exhibits):
    business = configuration.museum.business
    experience = business.visitor_experience
    questionnaire = tour_session.questionnaire or {}
    rhythm = str(questionnaire.get("rhythm_id") or "dialogue")
    durations = {"quick": 30, "dialogue": 60, "notebook": 90, "research": 120}
    if experience:
        durations.update(experience.rhythm_minutes)
    minutes = durations.get(rhythm, 60)
    persona = tour_session.persona
    selected_interest = next(
        (item for item in business.questionnaire.assumption_options if item.code == tour_session.assumption), None
    )
    topic = selected_interest.topic if selected_interest else ""
    catalog = {h["slug"]: h for h in halls if h.get("is_active")}
    by_source = {e.source_record_id: e for e in exhibits if e.is_active and e.hall in catalog}
    template = next((
        r for r in (experience.routes if experience else [])
        if r.persona == persona and r.planned_minutes == minutes
    ), None)
    if template:
        choices = {s.hall_slug: s.exhibit_ids for s in template.interest_variants.get(topic, [])}
        route = {
            "id": template.id, "planned_minutes": minutes, "source": "museum_configuration",
            "theme": business.routes[persona].theme, "summary": business.routes[persona].summary,
            "budget": {
                "intro": template.intro_minutes, "transfer": template.transfer_minutes,
                "report": template.report_minutes, "buffer": template.buffer_minutes,
            },
            "steps": [],
        }
        for step in template.steps:
            if step.hall_slug not in catalog:
                continue
            ids = choices.get(step.hall_slug, step.exhibit_ids)
            route["steps"].append({
                "hall_slug": step.hall_slug, "hall_name": catalog[step.hall_slug]["name"],
                "minutes": step.minutes, "task": step.task,
                "exhibits": [
                    {"id": by_source[eid].id, "source_record_id": eid, "name": by_source[eid].name}
                    for eid in ids if eid in by_source and by_source[eid].hall == step.hall_slug
                ],
            })
        route["planned_minutes"] = sum(s["minutes"] for s in route["steps"]) + sum(route["budget"].values())
        route["requested_minutes"] = minutes
    else:
        fallback = build_structured_route(minutes, [f"persona:{persona}"], halls=halls, business=business)
        route = {
            "id": f"default-{persona}-{minutes}", "planned_minutes": minutes,
            "requested_minutes": minutes, "source": "active_catalog", "theme": fallback["theme"],
            "summary": fallback["summary"], "budget": {}, "steps": [
                {
                    "hall_slug": s["hall_slug"], "hall_name": s["hall_name"],
                    "minutes": s["estimated_minutes"], "task": s["focus"],
                    "exhibits": [
                        {"id": e.id, "source_record_id": e.source_record_id, "name": e.name}
                        for e in exhibits if e.is_active and e.hall == s["hall_slug"]
                    ][:2],
                } for s in fallback["steps"]
            ],
        }
    route["interest_label"] = selected_interest.label if selected_interest else ""
    route["notice"] = "这是内容参观顺序与建议时长，可自主换厅或提前结束；计划不计入实际参观记录。"
    return route
