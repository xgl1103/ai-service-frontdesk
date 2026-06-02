"""API smoke tests for the FastAPI adapter."""

from __future__ import annotations

import os
import sys
from copy import deepcopy
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient

from backend.api import app
from storage import BUSINESS_FILE, LEADS_FILE, load_business_profile, load_leads, save_business_profile


os.environ["OPENAI_API_KEY"] = ""
os.environ["DEEPSEEK_API_KEY"] = ""

client = TestClient(app)


def test_health() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200, response.text
    assert response.json() == {"status": "ok"}


def test_cors() -> None:
    for origin in ("http://localhost:5173", "http://localhost:5174"):
        response = client.options(
            "/api/health",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
            },
        )
        assert response.status_code == 200, response.text
        assert response.headers["access-control-allow-origin"] == origin


def test_business_profile() -> None:
    original = deepcopy(load_business_profile())
    updated = {**original, "business_name": "安心到家服务 API 测试"}
    response = client.put("/api/business-profile", json=updated)
    assert response.status_code == 200, response.text
    assert response.json()["business_name"] == "安心到家服务 API 测试"
    assert client.get("/api/business-profile").json()["business_name"] == "安心到家服务 API 测试"
    save_business_profile(original)


def test_chat_and_leads() -> None:
    client.delete("/api/leads")
    first = client.post(
        "/api/chat",
        json={
            "message": "我家厨房水管漏水，明天上午能来修吗？",
            "current_lead": {},
            "chat_history": [],
        },
    )
    assert first.status_code == 200, first.text
    first_payload = first.json()
    assert first_payload["lead"]["service_need"] == "水管维修", first_payload
    assert "address" in first_payload["missing_fields"], first_payload
    assert "phone" in first_payload["missing_fields"], first_payload
    assert len(load_leads()) == 1

    second = client.post(
        "/api/chat",
        json={
            "message": "地址在浦东新区花园小区，电话13800138000",
            "current_lead": first_payload["lead"],
            "chat_history": [],
        },
    )
    assert second.status_code == 200, second.text
    second_payload = second.json()
    assert second_payload["lead"]["id"] == first_payload["lead"]["id"], second_payload
    assert second_payload["lead"]["phone"] == "13800138000", second_payload
    assert second_payload["missing_fields"] == [], second_payload
    assert second_payload["quote"], second_payload
    assert len(client.get("/api/leads").json()["items"]) == 1

    response = client.delete("/api/leads")
    assert response.status_code == 200, response.text
    assert response.json() == {"items": []}
    assert LEADS_FILE.exists()
    assert load_leads() == []


def test_knowledge_api() -> None:
    rebuild = client.post("/api/knowledge/rebuild")
    assert rebuild.status_code == 200, rebuild.text
    assert rebuild.json()["status"] == "ok", rebuild.json()

    status = client.get("/api/knowledge/status")
    assert status.status_code == 200, status.text
    assert status.json()["knowledge_dir_exists"] is True, status.json()

    files = client.get("/api/knowledge/files")
    assert files.status_code == 200, files.text
    names = {item["filename"] for item in files.json()["items"]}
    assert {"company.md", "pricing.md", "staff.md", "service_policy.md", "faq.md"} <= names

    company = client.get("/api/knowledge/files/company.md")
    assert company.status_code == 200, company.text
    assert "上海市浦东新区张江高科晨晖路 88 号" in company.json()["content"]

    search = client.post("/api/knowledge/search", json={"query": "深度保洁多少钱？", "top_k": 3})
    assert search.status_code == 200, search.text
    assert search.json()["items"], search.json()
    assert any("8-15 元/平方米" in item["content"] for item in search.json()["items"])


def test_knowledge_path_traversal_is_blocked() -> None:
    response = client.get("/api/knowledge/files/%2E%2E%2FREADME.md")
    assert response.status_code in {400, 404}, response.text

    response = client.get("/api/knowledge/files/README.md")
    assert response.status_code in {400, 404}, response.text


def main() -> None:
    original_files = {
        path: path.read_text(encoding="utf-8") if path.exists() else None
        for path in (BUSINESS_FILE, LEADS_FILE)
    }
    try:
        test_health()
        test_cors()
        test_business_profile()
        test_chat_and_leads()
        test_knowledge_api()
        test_knowledge_path_traversal_is_blocked()
    finally:
        for path, content in original_files.items():
            if content is None:
                path.unlink(missing_ok=True)
            else:
                path.write_text(content, encoding="utf-8")
    print("backend api_test passed")


if __name__ == "__main__":
    main()
