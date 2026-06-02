from __future__ import annotations

import inspect
import json
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st


DATA_DIR = Path("data")
BUSINESS_PATH = DATA_DIR / "business.json"
LEADS_PATH = DATA_DIR / "leads.json"
KNOWLEDGE_DIR = Path("knowledge")

DEFAULT_BUSINESS_PROFILE: dict[str, Any] = {
    "business_name": "安心到家维修",
    "industry": "家政/维修/装修",
    "service_area": "本市主城区",
    "business_hours": "周一至周日 09:00-20:00",
    "services": ["水管维修", "电路检修", "深度保洁", "小型安装"],
    "pricing_rules": "上门检测费 50-100 元；普通水管维修 150-400 元；深度保洁 8-15 元/平；最终价格以人工确认或现场情况为准。",
    "faq": "支持当天预约；紧急维修优先安排；报价为参考价，最终价格需人工确认。",
}

REQUIRED_LEAD_FIELDS = [
    ("service_need", "服务需求"),
    ("address", "服务地址/区域"),
    ("preferred_time", "期望上门时间"),
    ("phone", "联系电话"),
]

STATUS_LABELS = {
    "new": "新线索",
    "needs_info": "待补充信息",
    "quoted": "已生成报价",
    "handoff_required": "需人工接管",
    "信息收集中": "待补充信息",
    "待人工确认": "已生成报价",
    "需人工处理": "需人工接管",
}


def ensure_data_dir() -> None:
    DATA_DIR.mkdir(exist_ok=True)


def read_json(path: Path, default: Any) -> Any:
    ensure_data_dir()
    if not path.exists():
        return default

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default


def write_json(path: Path, payload: Any) -> None:
    ensure_data_dir()
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def import_storage_module() -> Any | None:
    try:
        import storage  # type: ignore

        return storage
    except Exception:
        return None


def import_graph_runner() -> Any | None:
    try:
        from graph import run_frontdesk_turn  # type: ignore

        return run_frontdesk_turn
    except Exception:
        return None


def import_knowledge_module() -> Any | None:
    for module_name in ("rag", "knowledge", "retriever", "graph"):
        try:
            module = __import__(module_name)
        except Exception:
            continue
        if any(
            hasattr(module, attr)
            for attr in (
                "retrieve_knowledge",
                "rebuild_knowledge_index",
                "build_knowledge_index",
                "get_knowledge_status",
            )
        ):
            return module
    return None


def load_business_profile() -> dict[str, Any]:
    storage = import_storage_module()
    if storage and hasattr(storage, "load_business_profile"):
        try:
            profile = storage.load_business_profile()
            return to_plain_dict(profile) or DEFAULT_BUSINESS_PROFILE.copy()
        except Exception:
            pass

    return read_json(BUSINESS_PATH, DEFAULT_BUSINESS_PROFILE.copy())


def save_business_profile(profile: dict[str, Any]) -> None:
    storage = import_storage_module()
    if storage and hasattr(storage, "save_business_profile"):
        try:
            storage.save_business_profile(profile)
            return
        except Exception:
            pass

    write_json(BUSINESS_PATH, profile)


def load_leads() -> list[dict[str, Any]]:
    storage = import_storage_module()
    if storage and hasattr(storage, "load_leads"):
        try:
            leads = storage.load_leads()
            return [to_plain_dict(lead) for lead in leads]
        except Exception:
            pass

    return read_json(LEADS_PATH, [])


def upsert_lead(lead: dict[str, Any]) -> None:
    storage = import_storage_module()
    if storage and hasattr(storage, "save_lead"):
        try:
            storage.save_lead(lead)
            return
        except Exception:
            pass

    leads = load_leads()
    lead_id = lead.get("id")
    found = False
    for index, existing in enumerate(leads):
        if existing.get("id") == lead_id:
            leads[index] = lead
            found = True
            break

    if not found:
        leads.append(lead)

    write_json(LEADS_PATH, leads)


def clear_saved_leads() -> None:
    write_json(LEADS_PATH, [])


def to_plain_dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    return {}


def normalize_services(raw: str) -> list[str]:
    return [item.strip() for item in raw.splitlines() if item.strip()]


def display_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        return "\n".join(f"{key}: {item}" for key, item in value.items())
    if isinstance(value, list):
        lines = []
        for item in value:
            if isinstance(item, dict):
                question = item.get("question", "")
                answer = item.get("answer", "")
                lines.append(f"{question}: {answer}".strip(": "))
            else:
                lines.append(str(item))
        return "\n".join(line for line in lines if line)
    return str(value)


def short_text(value: Any, max_length: int = 140) -> str:
    text = display_text(value).replace("\n", " ").strip()
    if len(text) <= max_length:
        return text
    return f"{text[:max_length]}..."


def status_label(status: Any) -> str:
    if not status:
        return "新线索"
    return STATUS_LABELS.get(str(status), str(status))


def value_or_pending(value: Any) -> str:
    return str(value) if value not in (None, "", [], {}) else "待补充"


def normalize_lead_for_ui(lead: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(lead)
    if normalized.get("handoff_required"):
        normalized["status"] = "handoff_required"
    elif not normalized.get("status"):
        normalized["status"] = "new"
    if normalized.get("quote") and normalized.get("status") in ("new", "needs_info", "待人工确认"):
        normalized["status"] = "quoted"
    return normalized


def list_knowledge_files() -> list[Path]:
    if not KNOWLEDGE_DIR.exists():
        return []
    return sorted(KNOWLEDGE_DIR.glob("*.md"))


def get_knowledge_status() -> dict[str, Any]:
    module = import_knowledge_module()
    files = list_knowledge_files()
    base_status = {
        "available": module is not None and hasattr(module, "retrieve_knowledge"),
        "module": module.__name__ if module else "",
        "file_count": len(files),
        "files": [path.name for path in files],
        "message": "",
    }

    if module and hasattr(module, "get_knowledge_status"):
        try:
            module_status = module.get_knowledge_status()
            if isinstance(module_status, dict):
                base_status.update(module_status)
            else:
                base_status["message"] = str(module_status)
        except Exception as error:
            base_status["message"] = f"知识库状态读取失败：{error}"

    if not KNOWLEDGE_DIR.exists():
        base_status["message"] = "未找到 knowledge/ 目录，当前使用无知识库 fallback。"
    elif not files:
        base_status["message"] = "knowledge/ 目录存在，但没有 .md 文件。"
    elif not base_status["available"]:
        base_status["message"] = "已发现本地 Markdown，但 retrieve_knowledge() 未接入。"
    elif not base_status.get("message"):
        base_status["message"] = "知识库检索已接入。"

    return base_status


def rebuild_knowledge_index() -> dict[str, Any]:
    module = import_knowledge_module()
    if module is None:
        return {
            "ok": False,
            "message": "未找到 RAG 模块，无法重建索引；页面已保持 fallback 状态。",
        }

    rebuild_fn = None
    for attr in ("rebuild_knowledge_index", "build_knowledge_index"):
        if hasattr(module, attr):
            rebuild_fn = getattr(module, attr)
            break

    if rebuild_fn is None:
        return {
            "ok": False,
            "message": "未找到重建索引函数，等待 RAG 子进程接入。",
        }

    try:
        result = call_flexible_function(
            rebuild_fn,
            {
                "knowledge_dir": KNOWLEDGE_DIR,
                "path": KNOWLEDGE_DIR,
                "directory": KNOWLEDGE_DIR,
            },
        )
        return {
            "ok": True,
            "message": display_text(result) or "知识库索引已重建。",
        }
    except Exception as error:
        return {"ok": False, "message": f"知识库索引重建失败：{error}"}


def call_flexible_function(func: Any, aliases: dict[str, Any]) -> Any:
    signature = inspect.signature(func)
    params = signature.parameters
    if not params:
        return func()

    accepts_kwargs = any(
        param.kind == inspect.Parameter.VAR_KEYWORD for param in params.values()
    )
    if accepts_kwargs:
        return func(**aliases)

    kwargs = {name: aliases[name] for name in params if name in aliases}
    if kwargs:
        return func(**kwargs)

    first_param = next(iter(params.values()))
    if first_param.default is inspect.Parameter.empty:
        return func(next(iter(aliases.values())))
    return func()


def retrieve_knowledge_hits(user_message: str) -> tuple[list[dict[str, Any]], str]:
    module = import_knowledge_module()
    if module is None or not hasattr(module, "retrieve_knowledge"):
        return [], "RAG 未接入：未找到 retrieve_knowledge()，当前未使用知识库来源。"

    try:
        result = call_flexible_function(
            getattr(module, "retrieve_knowledge"),
            {
                "query": user_message,
                "user_message": user_message,
                "message": user_message,
                "text": user_message,
                "k": 3,
                "top_k": 3,
            },
        )
        hits = normalize_knowledge_hits(result)
        if hits:
            return hits, "已检索知识库。"
        return [], "知识库可用，但本次没有命中来源。"
    except Exception as error:
        return [], f"知识库检索失败，已使用普通回复 fallback：{error}"


def normalize_knowledge_hits(result: Any) -> list[dict[str, Any]]:
    if result is None:
        return []
    if isinstance(result, dict):
        candidates = (
            result.get("sources")
            or result.get("documents")
            or result.get("results")
            or result.get("hits")
            or result.get("contexts")
            or []
        )
    else:
        candidates = result

    if isinstance(candidates, dict):
        candidates = [candidates]
    if not isinstance(candidates, list):
        return []

    hits = []
    for item in candidates:
        if isinstance(item, dict):
            metadata = item.get("metadata") or {}
            hits.append(
                {
                    "source": item.get("source") or metadata.get("source") or metadata.get("path") or "",
                    "title": item.get("title") or metadata.get("title") or metadata.get("filename") or "",
                    "score": item.get("score") or item.get("similarity") or item.get("distance") or "",
                    "content": item.get("content") or item.get("page_content") or item.get("text") or "",
                }
            )
            continue

        source = getattr(item, "metadata", {}) or {}
        hits.append(
            {
                "source": source.get("source") or source.get("path") or "",
                "title": source.get("title") or source.get("filename") or "",
                "score": getattr(item, "score", ""),
                "content": getattr(item, "page_content", "") or getattr(item, "content", ""),
            }
        )
    return hits


def extract_phone(text: str) -> str:
    match = re.search(r"(?<!\d)(1[3-9]\d{9}|(?:\+?\d[\d -]{6,}\d))(?!\d)", text)
    return match.group(1).strip() if match else ""


def extract_time(text: str) -> str:
    time_keywords = [
        "今天",
        "明天",
        "后天",
        "上午",
        "下午",
        "晚上",
        "周末",
        "周一",
        "周二",
        "周三",
        "周四",
        "周五",
        "周六",
        "周日",
    ]
    hits = [keyword for keyword in time_keywords if keyword in text]
    return " ".join(hits)


def extract_service_need(text: str, business_profile: dict[str, Any]) -> str:
    service_keywords = {
        "水管维修": ["水管", "漏水", "下水", "管道"],
        "电路检修": ["电路", "跳闸", "插座", "灯", "电"],
        "深度保洁": ["保洁", "清洁", "打扫", "深度"],
        "小型安装": ["安装", "组装", "挂画", "置物架"],
    }
    for service, keywords in service_keywords.items():
        if any(keyword in text for keyword in keywords):
            return service

    for service in business_profile.get("services", []):
        if service and service in text:
            return service

    return ""


def extract_address(text: str) -> str:
    address_patterns = [
        r"([^，。,.\n]{2,20}(?:区|县|镇|街道|小区|路|街|号楼|单元|室))",
        r"(地址[:：]\s*[^，。,.\n]{2,40})",
    ]
    for pattern in address_patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).replace("地址：", "").replace("地址:", "").strip()
    return ""


def guess_urgency(text: str) -> str:
    if any(keyword in text for keyword in ["马上", "立刻", "紧急", "严重", "一直漏", "停电"]):
        return "高"
    if any(keyword in text for keyword in ["今天", "明天", "尽快"]):
        return "中"
    return "普通"


def make_quote(lead: dict[str, Any], business_profile: dict[str, Any]) -> str:
    service = lead.get("service_need") or "相关服务"
    pricing_rules = business_profile.get("pricing_rules") or "最终价格需人工确认。"
    return f"{service}参考报价：{pricing_rules} 请以人工确认或现场情况为准。"


def fallback_run_frontdesk_turn(
    *,
    user_message: str,
    business_profile: dict[str, Any],
    messages: list[dict[str, str]],
    current_lead: dict[str, Any],
) -> dict[str, Any]:
    now = datetime.now().isoformat(timespec="seconds")
    lead = dict(current_lead or {})
    lead.setdefault("id", str(uuid.uuid4()))
    lead.setdefault("created_at", now)
    lead["updated_at"] = now

    extracted = {
        "phone": extract_phone(user_message),
        "preferred_time": extract_time(user_message),
        "service_need": extract_service_need(user_message, business_profile),
        "address": extract_address(user_message),
        "urgency": guess_urgency(user_message),
    }
    for key, value in extracted.items():
        if value and not lead.get(key):
            lead[key] = value

    if any(keyword in user_message for keyword in ["投诉", "弄坏", "赔偿", "危险", "起火", "燃气"]):
        lead["status"] = "handoff_required"
        assistant_reply = "这类情况需要人工尽快接管。我已经把这条线索标记为需人工处理，请留下联系电话和地址，工作人员会优先联系您。"
        return {
            "assistant_reply": assistant_reply,
            "lead": lead,
            "missing_fields": [],
            "quote": lead.get("quote", ""),
            "handoff_required": True,
        }

    missing_fields = [
        label for field, label in REQUIRED_LEAD_FIELDS if not lead.get(field)
    ]
    if missing_fields:
        lead["status"] = "needs_info"
        questions = "、".join(missing_fields[:3])
        assistant_reply = f"可以，我先帮您登记。还需要确认：{questions}。方便补充一下吗？"
        quote = ""
    else:
        lead["status"] = "quoted"
        quote = lead.get("quote") or make_quote(lead, business_profile)
        lead["quote"] = quote
        assistant_reply = f"信息已经基本齐了。{quote} 我会建议工作人员尽快确认具体时间和最终价格。"

    lead["summary"] = build_lead_summary(lead)
    return {
        "assistant_reply": assistant_reply,
        "lead": lead,
        "missing_fields": missing_fields,
        "quote": quote,
        "handoff_required": False,
    }


def build_lead_summary(lead: dict[str, Any]) -> str:
    parts = [
        lead.get("service_need"),
        lead.get("preferred_time"),
        lead.get("address"),
        lead.get("urgency"),
    ]
    return " / ".join(str(part) for part in parts if part)


def call_run_frontdesk_turn(
    *,
    user_message: str,
    business_profile: dict[str, Any],
    messages: list[dict[str, str]],
    current_lead: dict[str, Any],
) -> dict[str, Any]:
    runner = import_graph_runner()
    if runner is None:
        return fallback_run_frontdesk_turn(
            user_message=user_message,
            business_profile=business_profile,
            messages=messages,
            current_lead=current_lead,
        )

    state = {
        "user_message": user_message,
        "business_profile": business_profile,
        "messages": messages,
        "current_lead": current_lead,
        "lead": current_lead,
    }

    try:
        signature = inspect.signature(runner)
        params = signature.parameters
        if len(params) == 1 and "state" in params:
            return normalize_turn_result(runner(state))

        kwargs = {}
        aliases = {
            "user_message": user_message,
            "message": user_message,
            "input_text": user_message,
            "customer_message": user_message,
            "business_profile": business_profile,
            "profile": business_profile,
            "messages": messages,
            "chat_history": messages,
            "history": messages,
            "current_lead": current_lead,
            "lead": current_lead,
            "state": state,
        }
        accepts_kwargs = any(
            param.kind == inspect.Parameter.VAR_KEYWORD
            for param in params.values()
        )
        if accepts_kwargs:
            kwargs = {
                "user_message": user_message,
                "business_profile": business_profile,
                "messages": messages,
                "current_lead": current_lead,
            }
        else:
            kwargs = {name: aliases[name] for name in params if name in aliases}

        return normalize_turn_result(runner(**kwargs))
    except Exception as error:
        result = fallback_run_frontdesk_turn(
            user_message=user_message,
            business_profile=business_profile,
            messages=messages,
            current_lead=current_lead,
        )
        result["assistant_reply"] = (
            f"{result['assistant_reply']}\n\n提示：graph.py 调用失败，当前使用界面内置 fallback。错误：{error}"
        )
        return result


def normalize_turn_result(result: Any) -> dict[str, Any]:
    if isinstance(result, str):
        return {
            "assistant_reply": result,
            "lead": {},
            "missing_fields": [],
            "quote": "",
            "handoff_required": False,
            "knowledge_sources": [],
            "knowledge_status": "RAG 未接入：本次没有知识库来源。",
        }

    payload = to_plain_dict(result)
    lead = (
        payload.get("lead")
        or payload.get("current_lead")
        or payload.get("updated_lead")
        or {}
    )
    assistant_reply = (
        payload.get("assistant_reply")
        or payload.get("reply")
        or payload.get("message")
        or payload.get("content")
        or "已收到，我会继续帮您登记。"
    )
    lead = to_plain_dict(lead)
    quote = payload.get("quote", "")
    if quote and not lead.get("quote"):
        lead["quote"] = quote
    if payload.get("handoff_required"):
        lead["handoff_required"] = True
        lead["status"] = "handoff_required"
    elif payload.get("missing_fields"):
        lead.setdefault("status", "needs_info")

    return {
        "assistant_reply": assistant_reply,
        "lead": normalize_lead_for_ui(lead),
        "missing_fields": payload.get("missing_fields", []),
        "quote": quote,
        "handoff_required": payload.get("handoff_required", False),
        "knowledge_sources": normalize_knowledge_hits(
            payload.get("knowledge_sources")
            or payload.get("sources")
            or payload.get("retrieved_context")
            or payload.get("contexts")
            or []
        ),
        "knowledge_status": payload.get("knowledge_status", ""),
    }


def init_session_state() -> None:
    if "business_profile" not in st.session_state:
        st.session_state.business_profile = load_business_profile()
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "current_lead" not in st.session_state:
        st.session_state.current_lead = {}
    if "leads" not in st.session_state:
        st.session_state.leads = load_leads()
    if "knowledge_status" not in st.session_state:
        st.session_state.knowledge_status = get_knowledge_status()
    if "last_knowledge_hits" not in st.session_state:
        st.session_state.last_knowledge_hits = []
    if "last_knowledge_message" not in st.session_state:
        st.session_state.last_knowledge_message = st.session_state.knowledge_status.get("message", "")


def render_sidebar() -> None:
    profile = st.session_state.business_profile

    with st.sidebar:
        st.header("商家配置")
        with st.form("business_profile_form"):
            business_name = st.text_input("商家名称", value=profile.get("business_name", ""))
            industry = st.text_input("服务行业", value=profile.get("industry", ""))
            service_area = st.text_input("服务区域", value=profile.get("service_area", ""))
            business_hours = st.text_input("营业时间", value=profile.get("business_hours", ""))
            services = st.text_area(
                "服务项目",
                value=display_text(profile.get("services", [])),
                height=120,
            )
            pricing_rules = st.text_area(
                "价格规则",
                value=display_text(profile.get("pricing_rules", "")),
                height=130,
            )
            faq = st.text_area("常见问题 FAQ", value=display_text(profile.get("faq", "")), height=120)
            submitted = st.form_submit_button("保存配置", use_container_width=True)

        if submitted:
            updated_profile = {
                "business_name": business_name.strip(),
                "industry": industry.strip(),
                "service_area": service_area.strip(),
                "business_hours": business_hours.strip(),
                "services": normalize_services(services),
                "pricing_rules": pricing_rules.strip(),
                "faq": faq.strip(),
            }
            st.session_state.business_profile = updated_profile
            save_business_profile(updated_profile)
            st.success("商家配置已保存")

        if st.button("开始新的客户咨询", use_container_width=True):
            st.session_state.messages = []
            st.session_state.current_lead = {}
            st.rerun()

        if st.button("清空当前会话", use_container_width=True):
            st.session_state.messages = []
            st.session_state.current_lead = {}
            st.rerun()

        if st.button("清空历史线索", use_container_width=True):
            clear_saved_leads()
            st.session_state.leads = []
            st.session_state.current_lead = {}
            st.success("历史线索已清空")
            st.rerun()


def render_chat() -> None:
    st.subheader("客户聊天窗口")

    for message in st.session_state.messages:
        role = message.get("role", "assistant")
        content = message.get("content", "")
        with st.chat_message(role):
            st.write(content)

    user_message = st.chat_input("输入客户消息，例如：我家厨房水管漏水，明天上午能来修吗？")
    if not user_message:
        return

    st.session_state.messages.append({"role": "user", "content": user_message})
    result = call_run_frontdesk_turn(
        user_message=user_message,
        business_profile=st.session_state.business_profile,
        messages=st.session_state.messages,
        current_lead=st.session_state.current_lead,
    )

    assistant_reply = result["assistant_reply"]
    lead = result.get("lead", {}) or st.session_state.current_lead
    if lead:
        lead.setdefault("id", str(uuid.uuid4()))
        lead["summary"] = lead.get("summary") or build_lead_summary(lead)
        lead = normalize_lead_for_ui(lead)
        upsert_lead(lead)
        st.session_state.current_lead = lead
        st.session_state.leads = load_leads()

    knowledge_hits = result.get("knowledge_sources") or []
    knowledge_message = result.get("knowledge_status", "")
    if not knowledge_hits:
        knowledge_hits, knowledge_message = retrieve_knowledge_hits(user_message)
    elif not knowledge_message:
        knowledge_message = "本次回复已返回知识库来源。"
    st.session_state.last_knowledge_hits = knowledge_hits
    st.session_state.last_knowledge_message = knowledge_message

    st.session_state.messages.append({"role": "assistant", "content": assistant_reply})
    st.rerun()


def render_knowledge_panel() -> None:
    st.subheader("知识库")

    status = st.session_state.knowledge_status
    status_columns = st.columns(4)
    status_columns[0].metric("RAG 状态", "可用" if status.get("available") else "Fallback")
    status_columns[1].metric("Markdown 文件", str(status.get("file_count", 0)))
    status_columns[2].metric("检索模块", status.get("module") or "未接入")
    status_columns[3].metric("知识目录", str(KNOWLEDGE_DIR))

    if status.get("message"):
        if status.get("available"):
            st.success(status["message"])
        else:
            st.info(status["message"])

    button_left, button_right = st.columns(2)
    with button_left:
        if st.button("重建知识库索引", use_container_width=True):
            result = rebuild_knowledge_index()
            st.session_state.knowledge_status = get_knowledge_status()
            st.session_state.last_knowledge_message = result["message"]
            if result["ok"]:
                st.success(result["message"])
            else:
                st.warning(result["message"])
    with button_right:
        if st.button("查看知识库状态", use_container_width=True):
            st.session_state.knowledge_status = get_knowledge_status()
            st.session_state.last_knowledge_message = st.session_state.knowledge_status.get("message", "")
            st.rerun()

    files = status.get("files") or []
    if files:
        st.caption("本地知识文件：" + "、".join(files[:8]))

    st.markdown("**本次命中的知识来源**")
    if st.session_state.last_knowledge_message:
        st.caption(st.session_state.last_knowledge_message)

    hits = st.session_state.last_knowledge_hits
    if not hits:
        st.info("本次暂无知识来源命中。")
        return

    rows = []
    for hit in hits:
        rows.append(
            {
                "source": hit.get("source", ""),
                "title": hit.get("title", ""),
                "score": hit.get("score", ""),
                "content": short_text(hit.get("content", "")),
            }
        )
    st.dataframe(rows, use_container_width=True, hide_index=True)


def render_current_lead() -> None:
    st.subheader("当前线索")
    lead = st.session_state.current_lead
    if not lead:
        st.info("还没有当前线索。客户发起咨询后会显示在这里。")
        return

    columns = st.columns(4)
    columns[0].metric("服务需求", value_or_pending(lead.get("service_need")))
    columns[1].metric("联系电话", value_or_pending(lead.get("phone")))
    columns[2].metric("期望时间", value_or_pending(lead.get("preferred_time")))
    columns[3].metric("状态", status_label(lead.get("status")))

    detail_left, detail_right = st.columns(2)
    with detail_left:
        st.text_input("服务需求", value=value_or_pending(lead.get("service_need")), disabled=True)
        st.text_input("联系电话", value=value_or_pending(lead.get("phone")), disabled=True)
        st.text_input("服务地址", value=value_or_pending(lead.get("address")), disabled=True)
        st.text_input("期望时间", value=value_or_pending(lead.get("preferred_time")), disabled=True)
    with detail_right:
        st.text_input("紧急程度", value=value_or_pending(lead.get("urgency")), disabled=True)
        st.text_input("预算范围", value=value_or_pending(lead.get("budget")), disabled=True)
        st.text_area("报价草稿", value=value_or_pending(lead.get("quote")), disabled=True, height=135)


def render_leads_board() -> None:
    st.subheader("历史线索看板")
    leads = st.session_state.leads
    if not leads:
        st.info("暂无历史线索。")
        return

    rows = []
    for lead in sorted(leads, key=lambda item: item.get("updated_at", ""), reverse=True):
        rows.append(
            {
                "状态": status_label(lead.get("status")),
                "需求": lead.get("service_need", ""),
                "电话": lead.get("phone", ""),
                "地址": lead.get("address", ""),
                "时间": lead.get("preferred_time", ""),
                "紧急度": lead.get("urgency", ""),
                "摘要": lead.get("summary", ""),
                "更新时间": lead.get("updated_at", ""),
            }
        )

    st.dataframe(rows, use_container_width=True, hide_index=True)


def main() -> None:
    st.set_page_config(page_title="AI Service Frontdesk", layout="wide")
    init_session_state()
    render_sidebar()

    st.title("AI Service Frontdesk")
    st.caption("本地服务商 AI 询盘、追问、报价草稿和线索看板 MVP")

    render_chat()
    st.divider()
    render_knowledge_panel()
    st.divider()
    render_current_lead()
    st.divider()
    render_leads_board()


if __name__ == "__main__":
    main()
