from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid4())


class BusinessProfile(BaseModel):
    business_name: str = "安心到家服务"
    industry: str = "本地家政/维修服务"
    service_area: str = "本市主城区"
    business_hours: str = "周一至周日 08:00-20:00"
    services: list[str] = Field(
        default_factory=lambda: [
            "水管维修",
            "电路检修",
            "深度保洁",
            "家电清洗",
        ]
    )
    pricing_rules: str | list[str] | dict[str, str] = Field(
        default_factory=lambda: [
            "水管维修：上门检测费 50-100 元，普通维修 150-400 元起",
            "电路检修：上门检测费 80-120 元，普通检修 200-500 元起",
            "深度保洁：8-15 元/平方米，按面积和脏污程度调整",
            "家电清洗：单台 80-300 元，按设备类型调整",
        ]
    )
    faq: str | list[dict[str, str]] = Field(
        default_factory=lambda: [
            {
                "question": "报价是否为最终价格？",
                "answer": "线上报价仅供参考，最终价格需师傅现场确认。",
            },
            {
                "question": "是否支持周末上门？",
                "answer": "支持周末预约，具体时间需要人工确认排班。",
            },
        ]
    )


class QuoteDraft(BaseModel):
    service_name: str = ""
    estimate_range: str = ""
    basis: list[str] = Field(default_factory=list)
    disclaimer: str = "此报价仅供参考，最终价格需人工或现场确认。"
    next_action: str = "请人工确认细节后再预约或承诺最终价格。"


class Lead(BaseModel):
    id: str = Field(default_factory=new_id)
    name: str = ""
    phone: str = ""
    address: str = ""
    service_need: str = ""
    preferred_time: str = ""
    urgency: Literal["unknown", "low", "medium", "high"] = "unknown"
    budget: str = ""
    status: Literal["new", "needs_info", "quoted", "handoff_required", "closed"] = "new"
    summary: str = ""
    quote: str | QuoteDraft = ""
    missing_fields: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)


class GraphState(BaseModel):
    messages: list[dict[str, str]] = Field(default_factory=list)
    business_profile: BusinessProfile = Field(default_factory=BusinessProfile)
    lead: Lead = Field(default_factory=Lead)
    missing_fields: list[str] = Field(default_factory=list)
    quote: str | QuoteDraft = ""
    handoff_required: bool = False
    assistant_reply: str = ""
    metadata: dict[str, Any] = Field(default_factory=dict)
