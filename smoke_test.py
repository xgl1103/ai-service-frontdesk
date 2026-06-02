from __future__ import annotations

import os
import importlib
import sys
from pathlib import Path

from graph import REQUIRED_FIELDS, run_frontdesk_turn


os.environ["OPENAI_API_KEY"] = ""
os.environ["DEEPSEEK_API_KEY"] = ""
os.environ["FRONTDESK_DISABLE_RAG"] = "1"


BUSINESS_PROFILE = {
    "business_name": "安心到家维修",
    "industry": "家政/维修/装修",
    "service_area": "本市主城区",
    "business_hours": "周一至周日 09:00-20:00",
    "services": ["水管维修", "电路检修", "深度保洁", "小型安装"],
    "pricing_rules": {
        "水管维修": "上门检测费 50-100 元，普通维修 150-400 元",
        "电路检修": "上门检测费 80-120 元，普通检修 200-500 元",
        "深度保洁": "8-15 元/平，按面积和脏污程度调整",
        "小型安装": "普通安装 100-300 元",
    },
    "faq": "支持当天预约；报价为参考价，最终价格需人工确认。",
}


def assert_missing_fields_are_names(result: dict) -> None:
    missing_fields = result["missing_fields"]
    assert all(field in REQUIRED_FIELDS for field in missing_fields), missing_fields
    assert "联系电话" not in missing_fields
    assert "服务地址" not in missing_fields
    assert "retrieved_sources" in result
    assert "retrieved_context" in result


def test_water_leak_missing_fields() -> dict:
    result = run_frontdesk_turn(
        "我家厨房水管漏水，明天上午能来修吗？",
        BUSINESS_PROFILE,
    )

    assert result["handoff_required"] is False
    assert result["lead"]["service_need"] == "水管维修"
    assert result["lead"]["preferred_time"] == "明天上午"
    assert "address" in result["missing_fields"]
    assert "phone" in result["missing_fields"]
    assert result["quote"] == ""
    assert_missing_fields_are_names(result)
    return result["lead"]


def test_followup_updates_same_lead_and_quotes(current_lead: dict) -> None:
    result = run_frontdesk_turn(
        "地址在浦东新区花园小区，电话13800138000",
        BUSINESS_PROFILE,
        current_lead=current_lead,
    )

    assert result["handoff_required"] is False
    assert result["lead"]["id"] == current_lead["id"]
    assert result["lead"]["service_need"] == "水管维修"
    assert result["lead"]["phone"] == "13800138000"
    assert "浦东新区花园小区" in result["lead"]["address"]
    assert result["missing_fields"] == []
    assert "水管维修" in result["quote"]
    assert "150-400" in result["quote"]
    assert "深度保洁" not in result["quote"]
    assert "8-15" not in result["quote"]
    assert_missing_fields_are_names(result)


def test_deep_cleaning_missing_fields() -> None:
    result = run_frontdesk_turn(
        "你们周末能做深度保洁吗？大概90平。",
        BUSINESS_PROFILE,
    )

    assert result["handoff_required"] is False
    assert result["lead"]["service_need"] == "深度保洁"
    assert result["lead"]["preferred_time"] in {"周末", "这周末", "本周末"}
    assert "address" in result["missing_fields"]
    assert "phone" in result["missing_fields"]
    assert result["quote"] == ""
    assert_missing_fields_are_names(result)


def test_complaint_handoff() -> None:
    result = run_frontdesk_turn(
        "刚才维修师傅把我家弄坏了，我要投诉。",
        BUSINESS_PROFILE,
    )

    assert result["handoff_required"] is True
    assert result["lead"]["status"] == "handoff_required"
    assert result["quote"] == ""
    assert "人工" in result["assistant_reply"]
    assert_missing_fields_are_names(result)


def test_rag_pricing_md_priority() -> None:
    os.environ["FRONTDESK_DISABLE_RAG"] = "0"
    rag_path = Path(__file__).with_name("rag.py")
    original = rag_path.read_text(encoding="utf-8") if rag_path.exists() else None
    rag_path.write_text(
        """
def retrieve(query, **kwargs):
    return {
        "context": "水管维修：RAG上门检测费 60 元；水管维修：RAG普通维修 180-360 元\\n深度保洁：RAG 9-16 元/平",
        "sources": ["knowledge/pricing.md"],
    }
""".strip()
        + "\n",
        encoding="utf-8",
    )
    importlib.invalidate_caches()
    sys.modules.pop("rag", None)
    try:
        result = run_frontdesk_turn(
            "我家厨房水管漏水，在浦东新区花园小区，明天上午，电话13800138000",
            BUSINESS_PROFILE,
        )
        assert result["missing_fields"] == []
        assert result["retrieved_sources"] == ["knowledge/pricing.md"]
        assert "RAG普通维修 180-360" in result["quote"]
        assert "深度保洁" not in result["quote"]
        assert "最终价格需要商家" in result["quote"]
    finally:
        sys.modules.pop("rag", None)
        importlib.invalidate_caches()
        if original is None:
            rag_path.unlink(missing_ok=True)
        else:
            rag_path.write_text(original, encoding="utf-8")
        os.environ["FRONTDESK_DISABLE_RAG"] = "1"


def test_rag_error_falls_back() -> None:
    os.environ["FRONTDESK_DISABLE_RAG"] = "0"
    rag_path = Path(__file__).with_name("rag.py")
    original = rag_path.read_text(encoding="utf-8") if rag_path.exists() else None
    rag_path.write_text(
        """
def retrieve_knowledge(query, **kwargs):
    raise RuntimeError("temporary rag failure")
""".strip()
        + "\n",
        encoding="utf-8",
    )
    importlib.invalidate_caches()
    sys.modules.pop("rag", None)
    try:
        result = run_frontdesk_turn(
            "我家厨房水管漏水，在浦东新区花园小区，明天上午，电话13800138000",
            BUSINESS_PROFILE,
        )
        assert result["missing_fields"] == []
        assert result["retrieved_sources"] == []
        assert result["retrieved_context"] == ""
        assert "150-400" in result["quote"]
        assert "最终价格需要商家" in result["quote"]
    finally:
        sys.modules.pop("rag", None)
        importlib.invalidate_caches()
        if original is None:
            rag_path.unlink(missing_ok=True)
        else:
            rag_path.write_text(original, encoding="utf-8")
        os.environ["FRONTDESK_DISABLE_RAG"] = "1"


def main() -> None:
    first_lead = test_water_leak_missing_fields()
    test_followup_updates_same_lead_and_quotes(first_lead)
    test_deep_cleaning_missing_fields()
    test_complaint_handoff()
    test_rag_pricing_md_priority()
    test_rag_error_falls_back()
    print("smoke_test passed")


if __name__ == "__main__":
    main()
