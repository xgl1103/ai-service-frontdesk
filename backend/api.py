"""FastAPI adapter for the AI Service Frontdesk core modules."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from graph import run_frontdesk_turn
from rag import get_knowledge_status, rebuild_knowledge_index, retrieve_knowledge
from storage import load_business_profile, load_leads, save_business_profile, save_lead


PROJECT_ROOT = Path(__file__).resolve().parents[1]
KNOWLEDGE_DIR = (PROJECT_ROOT / "knowledge").resolve()


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    current_lead: dict[str, Any] = Field(default_factory=dict)
    chat_history: list[dict[str, str]] = Field(default_factory=list)


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=4, ge=1, le=20)


app = FastAPI(title="AI Service Frontdesk API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/chat")
def chat(request: ChatRequest) -> dict[str, Any]:
    result = run_frontdesk_turn(
        user_message=request.message,
        business_profile=load_business_profile(),
        current_lead=request.current_lead,
        chat_history=request.chat_history,
    )
    lead = result.get("lead")
    if isinstance(lead, dict) and lead:
        result["lead"] = save_lead(lead)
    return result


@app.get("/api/leads")
def get_leads() -> dict[str, list[dict[str, Any]]]:
    return {"items": load_leads()}


@app.delete("/api/leads")
def delete_leads() -> dict[str, list[Any]]:
    _write_empty_leads_file()
    return {"items": []}


@app.get("/api/business-profile")
def get_business_profile() -> dict[str, Any]:
    return load_business_profile()


@app.put("/api/business-profile")
def put_business_profile(profile: dict[str, Any]) -> dict[str, Any]:
    return save_business_profile(profile)


@app.get("/api/knowledge/status")
def knowledge_status() -> dict[str, Any]:
    return get_knowledge_status()


@app.post("/api/knowledge/rebuild")
def knowledge_rebuild() -> dict[str, Any]:
    return rebuild_knowledge_index()


@app.get("/api/knowledge/files")
def knowledge_files() -> dict[str, list[dict[str, Any]]]:
    return {
        "items": [
            {
                "filename": path.name,
                "source": f"knowledge/{path.name}",
                "size": path.stat().st_size,
            }
            for path in _knowledge_markdown_files()
        ]
    }


@app.get("/api/knowledge/files/{filename}")
def knowledge_file(filename: str) -> dict[str, str]:
    path = _safe_knowledge_file(filename)
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as error:
        raise HTTPException(status_code=500, detail=f"Failed to read knowledge file: {error}") from error
    return {"filename": path.name, "source": f"knowledge/{path.name}", "content": content}


@app.post("/api/knowledge/search")
def knowledge_search(request: KnowledgeSearchRequest) -> dict[str, list[dict[str, Any]]]:
    return {"items": retrieve_knowledge(request.query, top_k=request.top_k)}


def _knowledge_markdown_files() -> list[Path]:
    if not KNOWLEDGE_DIR.exists():
        return []
    return sorted(path for path in KNOWLEDGE_DIR.glob("*.md") if path.is_file())


def _safe_knowledge_file(filename: str) -> Path:
    if not filename or Path(filename).name != filename:
        raise HTTPException(status_code=400, detail="Invalid knowledge filename.")
    if not filename.lower().endswith(".md"):
        raise HTTPException(status_code=400, detail="Only Markdown knowledge files are readable.")

    path = (KNOWLEDGE_DIR / filename).resolve()
    try:
        path.relative_to(KNOWLEDGE_DIR)
    except ValueError as error:
        raise HTTPException(status_code=400, detail="Invalid knowledge filename.") from error

    if not path.is_file():
        raise HTTPException(status_code=404, detail="Knowledge file not found.")
    return path


def _write_empty_leads_file() -> None:
    from storage import LEADS_FILE

    LEADS_FILE.parent.mkdir(parents=True, exist_ok=True)
    LEADS_FILE.write_text("[]\n", encoding="utf-8")
