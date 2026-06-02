"""Local JSON storage for the AI Service Frontdesk MVP."""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4


DATA_DIR = Path(__file__).resolve().parent / "data"
BUSINESS_FILE = DATA_DIR / "business.json"
LEADS_FILE = DATA_DIR / "leads.json"


DEFAULT_BUSINESS_PROFILE: dict[str, Any] = {
    "business_name": "安心到家服务",
    "industry": "本地家政/维修服务",
    "service_area": "本市主城区",
    "business_hours": "周一至周日 08:00-20:00",
    "services": [
        "水管维修",
        "电路检修",
        "深度保洁",
        "家电清洗",
    ],
    "pricing_rules": {
        "水管维修": "上门检测费 50-100 元，普通维修 150-400 元起",
        "电路检修": "上门检测费 80-120 元，普通检修 200-500 元起",
        "深度保洁": "8-15 元/平方米，按面积和脏污程度调整",
        "家电清洗": "单台 80-300 元，按设备类型调整",
    },
    "faq": [
        {
            "question": "报价是否为最终价格？",
            "answer": "线上报价仅供参考，最终价格需师傅现场确认。",
        },
        {
            "question": "是否支持周末上门？",
            "answer": "支持周末预约，具体时间需要人工确认排班。",
        },
    ],
}

VALID_LEAD_STATUSES = {"new", "needs_info", "quoted", "handoff_required", "closed"}
DEFAULT_LEAD: dict[str, Any] = {
    "name": "",
    "phone": "",
    "address": "",
    "service_need": "",
    "preferred_time": "",
    "urgency": "unknown",
    "budget": "",
    "status": "new",
    "summary": "",
    "quote": "",
    "missing_fields": [],
}


def load_business_profile() -> dict[str, Any]:
    """Load the business profile, creating a default file when needed."""

    _ensure_data_files()
    data = _read_json(BUSINESS_FILE, DEFAULT_BUSINESS_PROFILE)
    if not isinstance(data, dict) or not data:
        data = deepcopy(DEFAULT_BUSINESS_PROFILE)
        _write_json(BUSINESS_FILE, data)
    return _normalize_business_profile(data)


def save_business_profile(profile: Any) -> dict[str, Any]:
    """Persist a business profile and return the normalized dictionary."""

    normalized = _to_plain_data(profile)
    if not isinstance(normalized, dict):
        raise TypeError("Business profile must be a mapping or serializable object.")
    normalized = _normalize_business_profile(normalized)
    _ensure_data_files()
    _write_json(BUSINESS_FILE, normalized)
    return normalized


def load_leads() -> list[dict[str, Any]]:
    """Load all leads, returning an empty list when no usable data exists."""

    _ensure_data_files()
    data = _read_json(LEADS_FILE, [])
    if isinstance(data, list):
        return [_normalize_lead(lead, apply_defaults=True) for lead in data if isinstance(lead, dict)]
    _write_json(LEADS_FILE, [])
    return []


def save_lead(lead: Any) -> dict[str, Any]:
    """Create or replace a lead by id and return the saved record."""

    normalized = _normalize_lead(lead, apply_defaults=True)
    leads = load_leads()
    existing_index = _find_lead_index(leads, normalized["id"])
    now = _utc_now()

    if existing_index is None:
        normalized.setdefault("created_at", now)
        normalized["updated_at"] = now
        leads.append(normalized)
    else:
        previous = leads[existing_index]
        normalized = _merge_lead(previous, normalized)
        normalized["created_at"] = previous.get("created_at") or now
        normalized["updated_at"] = now
        leads[existing_index] = normalized

    _write_json(LEADS_FILE, leads)
    return normalized


def update_lead(lead_id: str, patch: Any) -> dict[str, Any]:
    """Patch an existing lead. If it does not exist, create a new lead."""

    if not lead_id:
        raise ValueError("lead_id is required.")

    patch_data = _to_plain_data(patch)
    if not isinstance(patch_data, dict):
        raise TypeError("Lead patch must be a mapping or serializable object.")
    patch_data = _normalize_lead(patch_data, apply_defaults=False)

    leads = load_leads()
    existing_index = _find_lead_index(leads, lead_id)
    now = _utc_now()

    if existing_index is None:
        updated = _normalize_lead(
            {"id": lead_id, **DEFAULT_LEAD, **patch_data, "created_at": now, "updated_at": now},
            apply_defaults=True,
        )
        leads.append(updated)
    else:
        updated = _merge_lead(leads[existing_index], patch_data)
        updated["id"] = lead_id
        updated["updated_at"] = now
        leads[existing_index] = updated

    _write_json(LEADS_FILE, leads)
    return updated


def _ensure_data_files() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not BUSINESS_FILE.exists():
        _write_json(BUSINESS_FILE, DEFAULT_BUSINESS_PROFILE)
    if not LEADS_FILE.exists():
        _write_json(LEADS_FILE, [])


def _read_json(path: Path, default: Any) -> Any:
    try:
        if not path.exists() or path.stat().st_size == 0:
            _write_json(path, default)
            return deepcopy(default)
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, OSError):
        _write_json(path, default)
        return deepcopy(default)


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)
        file.write("\n")


def _normalize_business_profile(profile: dict[str, Any]) -> dict[str, Any]:
    normalized = {**deepcopy(DEFAULT_BUSINESS_PROFILE), **profile}

    services = normalized.get("services")
    if isinstance(services, str):
        normalized["services"] = _split_lines(services)
    elif not isinstance(services, list):
        normalized["services"] = deepcopy(DEFAULT_BUSINESS_PROFILE["services"])

    pricing_rules = normalized.get("pricing_rules")
    if pricing_rules is None:
        normalized["pricing_rules"] = deepcopy(DEFAULT_BUSINESS_PROFILE["pricing_rules"])
    elif isinstance(pricing_rules, (str, list, dict)):
        normalized["pricing_rules"] = pricing_rules
    else:
        normalized["pricing_rules"] = str(pricing_rules)

    faq = normalized.get("faq")
    if faq is None:
        normalized["faq"] = deepcopy(DEFAULT_BUSINESS_PROFILE["faq"])
    elif isinstance(faq, str):
        normalized["faq"] = faq
    elif isinstance(faq, list):
        normalized["faq"] = [item for item in faq if isinstance(item, (dict, str))]
    else:
        normalized["faq"] = str(faq)

    return normalized


def _normalize_lead(lead: Any, *, apply_defaults: bool) -> dict[str, Any]:
    data = _to_plain_data(lead)
    if not isinstance(data, dict):
        raise TypeError("Lead must be a mapping or serializable object.")

    normalized = {**DEFAULT_LEAD, **data} if apply_defaults else dict(data)
    if apply_defaults:
        normalized.setdefault("id", str(uuid4()))

    if "status" in normalized and normalized.get("status") not in VALID_LEAD_STATUSES:
        normalized["status"] = "new"

    if "urgency" in normalized and not normalized.get("urgency"):
        normalized["urgency"] = "unknown"

    if "quote" in normalized:
        normalized["quote"] = _normalize_quote(normalized.get("quote"))

    if "missing_fields" in normalized and not isinstance(normalized.get("missing_fields"), list):
        normalized["missing_fields"] = _split_lines(normalized.get("missing_fields"))

    return normalized


def _normalize_quote(quote: Any) -> str | dict[str, Any]:
    quote_data = _to_plain_data(quote)
    if quote_data is None:
        return ""
    if isinstance(quote_data, (str, dict)):
        return quote_data
    return str(quote_data)


def _merge_lead(previous: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    merged = dict(previous)
    for key, value in incoming.items():
        if key in {"created_at", "updated_at"}:
            continue
        if _is_empty_value(value) and not _is_empty_value(previous.get(key)):
            continue
        merged[key] = value
    return _normalize_lead(merged, apply_defaults=True)


def _is_empty_value(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


def _split_lines(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [line.strip() for line in str(value).replace(",", "\n").splitlines() if line.strip()]


def _to_plain_data(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if hasattr(value, "dict"):
        return value.dict()
    return deepcopy(value)


def _find_lead_index(leads: list[dict[str, Any]], lead_id: str) -> int | None:
    for index, lead in enumerate(leads):
        if lead.get("id") == lead_id:
            return index
    return None


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
