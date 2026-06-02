from __future__ import annotations

import os

from graph import run_frontdesk_turn
from rag import get_knowledge_status, rebuild_knowledge_index, retrieve_knowledge


os.environ["OPENAI_API_KEY"] = ""
os.environ["DEEPSEEK_API_KEY"] = ""


BUSINESS_PROFILE = {
    "business_name": "安心到家服务",
    "industry": "本地家政/维修服务",
    "service_area": "上海市主城区",
    "business_hours": "周一至周日 08:30-20:00",
    "services": ["水管维修", "深度保洁", "家电清洗", "家居安装"],
    "pricing_rules": "优先使用 knowledge/pricing.md 中的价格资料，最终价格需人工确认。",
}


def assert_hit(query: str, expected_text: str) -> list[dict]:
    hits = retrieve_knowledge(query, top_k=3)
    combined = "\n".join(hit.get("content", "") for hit in hits)
    assert hits, query
    assert expected_text in combined, (query, hits)
    return hits


def test_status_and_rebuild() -> None:
    result = rebuild_knowledge_index()
    assert result["status"] == "ok", result
    assert result["chunk_count"] >= 5, result

    status = get_knowledge_status()
    assert status["knowledge_dir_exists"] is True, status
    assert status["source_count"] >= 5, status
    assert status["fallback_available"] is True, status


def test_retrieve_company_address() -> None:
    assert_hit("你们公司地址在哪？", "上海市浦东新区张江高科晨晖路 88 号")


def test_retrieve_staff() -> None:
    hits = retrieve_knowledge("王师傅能修水管吗？", top_k=4)
    combined = "\n".join(hit.get("content", "") for hit in hits)
    assert "张师傅" in combined or "水电维修师" in combined, hits


def test_retrieve_cleaning_price() -> None:
    assert_hit("深度保洁多少钱？", "8-15 元/平方米")


def test_retrieve_after_sales() -> None:
    assert_hit("维修后保修多久？", "30 天内")


def test_graph_returns_rag_fields() -> None:
    result = run_frontdesk_turn("你们公司地址在哪？", BUSINESS_PROFILE)
    assert result["retrieved_sources"], result
    assert "上海市浦东新区张江高科晨晖路 88 号" in result["retrieved_context"], result


def main() -> None:
    test_status_and_rebuild()
    test_retrieve_company_address()
    test_retrieve_staff()
    test_retrieve_cleaning_price()
    test_retrieve_after_sales()
    test_graph_returns_rag_fields()
    print("rag_smoke_test passed")


if __name__ == "__main__":
    main()
