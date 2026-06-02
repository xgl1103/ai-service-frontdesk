from __future__ import annotations

import json
import os
import re
from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, List, Optional, TypedDict

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - dependency may not be installed yet
    load_dotenv = None

try:
    from langchain_openai import ChatOpenAI
except ImportError:  # pragma: no cover
    ChatOpenAI = None

try:
    from langgraph.graph import END, StateGraph
except ImportError:  # pragma: no cover
    END = "__end__"
    StateGraph = None


REQUIRED_FIELDS = ["service_need", "address", "preferred_time", "phone"]
OPTIONAL_FIELDS = ["name", "urgency", "budget"]
ALL_LEAD_FIELDS = REQUIRED_FIELDS + OPTIONAL_FIELDS

HANDOFF_KEYWORDS = [
    "投诉",
    "退款",
    "退钱",
    "索赔",
    "赔偿",
    "纠纷",
    "弄坏",
    "损坏",
    "吵架",
    "生气",
    "威胁",
    "报警",
    "危险",
    "起火",
    "着火",
    "冒烟",
    "爆炸",
    "触电",
    "漏电",
    "煤气",
    "燃气",
    "燃气泄漏",
    "煤气泄漏",
    "淹水",
    "受伤",
    "流血",
    "急救",
    "医院",
    "法律",
    "律师",
]

SERVICE_KEYWORDS = {
    "水管维修": ["水管", "漏水", "渗水", "下水道", "堵", "马桶", "龙头", "管道", "水槽", "地漏"],
    "电路维修": ["电路", "跳闸", "插座", "电线", "灯", "漏电", "短路", "断电"],
    "家电维修": ["空调", "冰箱", "洗衣机", "热水器", "油烟机", "家电"],
    "深度保洁": ["保洁", "清洁", "打扫", "深度", "开荒", "擦玻璃", "清洗", "卫生"],
    "门锁维修": ["锁", "钥匙", "开锁", "换锁"],
    "小型安装": ["安装", "组装", "挂画", "置物架", "窗帘杆"],
}

FIELD_LABELS = {
    "name": "您的称呼",
    "phone": "联系电话",
    "address": "服务地址或所在区域",
    "service_need": "具体服务需求",
    "preferred_time": "期望上门时间",
    "urgency": "紧急程度",
    "budget": "预算范围",
}


class FrontdeskState(TypedDict, total=False):
    user_message: str
    business_profile: Dict[str, Any]
    current_lead: Dict[str, Any]
    chat_history: List[Dict[str, str]]
    lead: Dict[str, Any]
    missing_fields: List[str]
    retrieved_context: str
    retrieved_sources: List[str]
    quote: str
    handoff_required: bool
    assistant_reply: str
    use_llm: bool


def run_frontdesk_turn(
    user_message: str,
    business_profile: Any,
    current_lead: Optional[Any] = None,
    chat_history: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """Run one AI frontdesk turn and return reply, lead, quote, and routing flags.

    The function accepts plain dicts or Pydantic-like objects. It intentionally
    returns plain dicts so Streamlit/storage modules can consume it without
    importing LangGraph internals.
    """

    if load_dotenv:
        load_dotenv()

    initial_state: FrontdeskState = {
        "user_message": user_message.strip(),
        "business_profile": _to_dict(business_profile),
        "current_lead": _normalize_lead(current_lead),
        "chat_history": chat_history or [],
        "use_llm": _can_use_llm(),
    }

    graph = _build_graph()
    if graph is None:
        state = extract_node(initial_state)
        state = retrieve_node(state)
        state = missing_fields_node(state)
        state = reply_node(state)
        state = quote_node(state)
    else:
        state = graph.invoke(initial_state)

    return {
        "assistant_reply": state.get("assistant_reply", ""),
        "lead": state.get("lead", {}),
        "missing_fields": state.get("missing_fields", []),
        "quote": state.get("quote", ""),
        "handoff_required": state.get("handoff_required", False),
        "retrieved_sources": state.get("retrieved_sources", []),
        "retrieved_context": state.get("retrieved_context", ""),
    }


def _build_graph():
    if StateGraph is None:
        return None

    workflow = StateGraph(FrontdeskState)
    workflow.add_node("extract_node", extract_node)
    workflow.add_node("retrieve_node", retrieve_node)
    workflow.add_node("missing_fields_node", missing_fields_node)
    workflow.add_node("reply_node", reply_node)
    workflow.add_node("quote_node", quote_node)

    workflow.set_entry_point("extract_node")
    workflow.add_edge("extract_node", "retrieve_node")
    workflow.add_edge("retrieve_node", "missing_fields_node")
    workflow.add_edge("missing_fields_node", "reply_node")
    workflow.add_edge("reply_node", "quote_node")
    workflow.add_edge("quote_node", END)
    return workflow.compile()


def extract_node(state: FrontdeskState) -> FrontdeskState:
    lead = deepcopy(state.get("current_lead") or {})
    user_message = state.get("user_message", "")
    business_profile = state.get("business_profile", {})
    handoff_required = _needs_handoff(user_message)

    llm_extract = None
    if state.get("use_llm"):
        llm_extract = _extract_with_llm(user_message, business_profile, lead, state.get("chat_history", []))

    extracted = llm_extract or _extract_with_rules(user_message, business_profile)
    lead.update({key: value for key, value in extracted.items() if value not in (None, "", [])})

    lead.setdefault("id", _make_lead_id())
    lead.setdefault("status", "new")
    lead.setdefault("created_at", datetime.now().isoformat(timespec="seconds"))
    lead["updated_at"] = datetime.now().isoformat(timespec="seconds")

    if handoff_required:
        lead["status"] = "handoff_required"

    lead["summary"] = _build_summary(lead)

    next_state = dict(state)
    next_state["lead"] = lead
    next_state["handoff_required"] = handoff_required
    return next_state


def missing_fields_node(state: FrontdeskState) -> FrontdeskState:
    lead = state.get("lead", {})
    missing_fields = [field for field in REQUIRED_FIELDS if not _has_value(lead.get(field))]

    next_state = dict(state)
    next_state["missing_fields"] = missing_fields
    return next_state


def retrieve_node(state: FrontdeskState) -> FrontdeskState:
    if state.get("handoff_required"):
        next_state = dict(state)
        next_state.setdefault("retrieved_context", "")
        next_state.setdefault("retrieved_sources", [])
        return next_state

    query = _build_retrieval_query(state)
    context, sources = _retrieve_context(query, state)

    next_state = dict(state)
    next_state["retrieved_context"] = context
    next_state["retrieved_sources"] = sources
    return next_state


def reply_node(state: FrontdeskState) -> FrontdeskState:
    if state.get("handoff_required"):
        reply = (
            "这类情况需要人工马上接管。我已经帮您记录下来，商家会优先核实处理；"
            "如果涉及人身安全、燃气、漏电或火情，请先联系当地紧急服务。"
        )
    elif state.get("use_llm"):
        reply = _reply_with_llm(state) or _reply_with_rules(state)
    else:
        reply = _reply_with_rules(state)

    next_state = dict(state)
    next_state["assistant_reply"] = reply
    return next_state


def quote_node(state: FrontdeskState) -> FrontdeskState:
    lead = deepcopy(state.get("lead") or {})
    missing_fields = state.get("missing_fields", [])
    quote = ""

    if not state.get("handoff_required") and not missing_fields:
        if state.get("use_llm"):
            quote = _quote_with_llm(state) or _quote_with_rules(state)
        else:
            quote = _quote_with_rules(state)
        lead["quote"] = quote
        lead["status"] = "quoted"
        lead["summary"] = _build_summary(lead)

    next_state = dict(state)
    next_state["lead"] = lead
    next_state["quote"] = quote
    if quote:
        next_state["assistant_reply"] = f"{state.get('assistant_reply', '')}\n\n{quote}".strip()
    return next_state


def _can_use_llm() -> bool:
    return bool(_configured_secret("DEEPSEEK_API_KEY") or _configured_secret("OPENAI_API_KEY")) and ChatOpenAI is not None


def _llm() -> Any:
    deepseek_api_key = _configured_secret("DEEPSEEK_API_KEY")
    if deepseek_api_key:
        return ChatOpenAI(
            api_key=deepseek_api_key,
            base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").strip(),
            model=os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash").strip(),
            temperature=0.2,
        )

    return ChatOpenAI(
        api_key=_configured_secret("OPENAI_API_KEY"),
        model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip(),
        temperature=0.2,
    )


def _configured_secret(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value or value.lower().startswith("your_"):
        return ""
    return value


def _extract_with_llm(
    user_message: str,
    business_profile: Dict[str, Any],
    current_lead: Dict[str, Any],
    chat_history: List[Dict[str, str]],
) -> Optional[Dict[str, Any]]:
    prompt = f"""
你是本地服务商 AI 前台的信息抽取器。请只输出 JSON，不要 Markdown。

需要抽取的字段：
name, phone, address, service_need, preferred_time, urgency, budget

如果字段未知，用空字符串。不要编造。

商家资料：
{json.dumps(business_profile, ensure_ascii=False)}

当前线索：
{json.dumps(current_lead, ensure_ascii=False)}

最近对话：
{json.dumps(chat_history[-8:], ensure_ascii=False)}

客户最新消息：
{user_message}
"""
    try:
        response = _llm().invoke(prompt)
        return _safe_json_dict(_message_content(response))
    except Exception:
        return None


def _reply_with_llm(state: FrontdeskState) -> Optional[str]:
    lead = state.get("lead", {})
    missing_fields = state.get("missing_fields", [])
    retrieved_context = state.get("retrieved_context", "")
    prompt = f"""
你是本地服务商的真实前台。请用中文简短回复客户，语气自然。

规则：
1. 信息不足时，优先追问缺失字段，每次最多问 3 个问题。
2. 不要承诺最终价格、最终时间或一定能上门。
3. 不要输出内部字段名。
4. 如果信息足够，告知已登记，稍后给参考报价。
5. 如果检索资料为空，不要编造商家知识或价格，提示需要人工确认。

商家资料：
{json.dumps(state.get("business_profile", {}), ensure_ascii=False)}

检索资料：
{retrieved_context or "无"}

当前线索：
{json.dumps(lead, ensure_ascii=False)}

缺失字段：
{", ".join(missing_fields) or "无"}

客户最新消息：
{state.get("user_message", "")}
"""
    try:
        response = _llm().invoke(prompt)
        return _message_content(response).strip()
    except Exception:
        return None


def _quote_with_llm(state: FrontdeskState) -> Optional[str]:
    prompt = f"""
你是本地服务商前台。请基于线索、检索资料和商家价格规则，生成中文报价草稿。

要求：
1. 必须说明这是参考报价，最终价格需人工或现场确认。
2. 不要编造过细价格。如果价格规则不足，给区间或说明需确认。
3. 如果检索资料中包含 pricing.md 内容，优先引用 pricing.md 的相关价格。
4. 如果检索不到相关价格资料，不要编造，提示需要人工确认。
5. 输出 2-4 行即可。

商家资料：
{json.dumps(state.get("business_profile", {}), ensure_ascii=False)}

检索资料：
{state.get("retrieved_context", "") or "无"}

检索来源：
{json.dumps(state.get("retrieved_sources", []), ensure_ascii=False)}

线索：
{json.dumps(state.get("lead", {}), ensure_ascii=False)}
"""
    try:
        response = _llm().invoke(prompt)
        return _message_content(response).strip()
    except Exception:
        return None


def _extract_with_rules(user_message: str, business_profile: Dict[str, Any]) -> Dict[str, Any]:
    text = user_message.strip()
    extracted: Dict[str, Any] = {}

    phone = _extract_phone(text)
    if phone:
        extracted["phone"] = phone

    service_need = _detect_service_need(text, business_profile)
    if service_need:
        extracted["service_need"] = service_need

    preferred_time = _detect_time(text)
    if preferred_time:
        extracted["preferred_time"] = preferred_time

    address = _detect_address(text)
    if address:
        extracted["address"] = address

    budget = _detect_budget(text)
    if budget:
        extracted["budget"] = budget

    if any(word in text for word in ["急", "马上", "立刻", "现在", "尽快", "严重"]):
        extracted["urgency"] = "高"
    elif any(word in text for word in ["明天", "周末", "这周", "预约"]):
        extracted["urgency"] = "中"

    name_match = re.search(r"(?:我叫|本人|姓名|称呼)[：:\s]*([\u4e00-\u9fa5A-Za-z]{2,12})", text)
    if name_match:
        extracted["name"] = name_match.group(1)

    return extracted


def _reply_with_rules(state: FrontdeskState) -> str:
    missing_fields = state.get("missing_fields", [])
    lead = state.get("lead", {})
    retrieved_context = state.get("retrieved_context", "")

    knowledge_reply = _answer_knowledge_query(state)
    if knowledge_reply:
        return knowledge_reply

    if missing_fields:
        questions = [FIELD_LABELS[field] for field in missing_fields[:3]]
        service = lead.get("service_need") or "您的需求"
        return f"可以的，我先帮您登记{service}。请补充一下：{'、'.join(questions)}。"

    if not retrieved_context:
        return "信息已经记录完整，但我暂时没有检索到可直接引用的资料。可先生成参考报价，最终价格和上门时间需要商家人工确认。"

    return "信息已经记录完整，我先为您生成参考报价，最终价格和上门时间还需要商家人工确认。"


def _answer_knowledge_query(state: FrontdeskState) -> str:
    query = str(state.get("user_message", "")).strip()
    context = str(state.get("retrieved_context", "")).strip()
    if not query or not context or not _is_knowledge_query(query):
        return ""

    sources = state.get("retrieved_sources", [])
    source_hint = _format_source_hint(sources)

    if any(word in query for word in ["地址", "在哪", "哪里", "位置", "公司"]):
        line = _find_context_line(context, ["公司地址", "位于"])
        if line:
            return f"{_clean_context_line(line)}{source_hint}"

    if any(word in query for word in ["保修", "保多久", "售后", "复查", "维修后"]):
        line = _find_context_line(context, ["维修服务完成后", "30 天内", "同一故障点"])
        if line:
            return f"{_clean_context_line(line)}{source_hint}"

    if any(word in query for word in ["多少钱", "价格", "报价", "收费", "费用"]):
        service_need = str(state.get("lead", {}).get("service_need", ""))
        line = _find_price_line(context, service_need or query)
        if line:
            return f"{_clean_context_line(line)}。线上价格仅供参考，最终价格需人工或现场确认{source_hint}"

    if any(word in query for word in ["师傅", "员工", "人员", "谁", "王师傅"]):
        if "王师傅" in query and "王师傅" not in context:
            plumber = _find_context_line(context, ["张师傅", "水电维修师"])
            if plumber:
                return (
                    f"知识库里没有登记“王师傅”。水管维修相关资料显示：{_clean_context_line(plumber)}。"
                    f"能否上门仍需客服根据排班确认{source_hint}"
                )
        line = _find_context_line(context, ["师傅", "专长", "水电维修"])
        if line:
            return f"{_clean_context_line(line)}。具体派单需要客服根据区域、时间和排班确认{source_hint}"

    line = _first_informative_context_line(context)
    if line:
        return f"{_clean_context_line(line)}{source_hint}"
    return ""


def _quote_with_rules(state: FrontdeskState) -> str:
    lead = state.get("lead", {})
    business_profile = state.get("business_profile", {})
    service_need = str(lead.get("service_need", "本次服务"))
    rag_pricing = _select_pricing_from_retrieved_context(service_need, state)
    pricing_rules = business_profile.get("pricing_rules") or business_profile.get("pricing") or ""
    default_price = _default_price_for_service(service_need)
    pricing_text = rag_pricing or _select_relevant_pricing(service_need, pricing_rules)
    price_hint = pricing_text or default_price
    area_hint = _extract_area_hint(str(lead.get("service_need", "")) + " " + str(lead.get("summary", "")))
    if not area_hint:
        area_hint = _extract_area_hint(str(state.get("user_message", "")))
    basis = f"；已记录地址：{lead.get('address')}" if lead.get("address") else ""
    if area_hint and "保洁" in service_need:
        basis += f"；面积：{area_hint}"
    source_hint = "；参考资料：pricing.md" if rag_pricing else ""

    return (
        f"报价草稿：{service_need}的参考价格为 {price_hint}{basis}{source_hint}。"
        f"该报价仅供初步沟通，最终价格需要商家根据现场情况或详细需求确认。"
    )


def _needs_handoff(text: str) -> bool:
    return any(keyword in text for keyword in HANDOFF_KEYWORDS)


def _build_retrieval_query(state: FrontdeskState) -> str:
    lead = state.get("lead", {})
    parts = [
        state.get("user_message", ""),
        str(lead.get("service_need", "")),
        str(lead.get("address", "")),
        str(lead.get("preferred_time", "")),
    ]
    return " ".join(part for part in parts if part).strip()


def _retrieve_context(query: str, state: FrontdeskState) -> tuple[str, List[str]]:
    if not query:
        return "", []
    if os.getenv("FRONTDESK_DISABLE_RAG", "").strip().lower() in {"1", "true", "yes"}:
        return "", []

    try:
        import rag  # type: ignore
    except Exception:
        return "", []

    try:
        result = _call_rag_retriever(rag, query, state)
        return _normalize_retrieval_result(result)
    except Exception:
        return "", []


def _call_rag_retriever(rag_module: Any, query: str, state: FrontdeskState) -> Any:
    candidates = [
        "retrieve_knowledge",
        "retrieve",
        "retrieve_context",
        "search",
        "query",
        "rag_search",
    ]
    for name in candidates:
        func = getattr(rag_module, name, None)
        if callable(func):
            return _call_retriever_func(func, query, state)
    return None


def _call_retriever_func(func: Any, query: str, state: FrontdeskState) -> Any:
    kwargs = {
        "query": query,
        "user_message": state.get("user_message", ""),
        "business_profile": state.get("business_profile", {}),
        "lead": state.get("lead", {}),
    }
    try:
        import inspect

        signature = inspect.signature(func)
        params = signature.parameters
        if any(param.kind == inspect.Parameter.VAR_KEYWORD for param in params.values()):
            return func(**kwargs)
        accepted = {name: value for name, value in kwargs.items() if name in params}
        if accepted:
            return func(**accepted)
    except Exception:
        pass
    return func(query)


def _normalize_retrieval_result(result: Any) -> tuple[str, List[str]]:
    if result is None:
        return "", []

    if isinstance(result, str):
        return result.strip(), []

    if isinstance(result, dict):
        context = result.get("context") or result.get("retrieved_context") or result.get("text") or result.get("content") or ""
        raw_sources = result.get("sources") or result.get("retrieved_sources") or result.get("source") or []
        return str(context).strip(), _normalize_sources(raw_sources)

    if isinstance(result, list):
        context_parts: List[str] = []
        sources: List[str] = []
        for item in result:
            item_context, item_sources = _normalize_retrieval_result(item)
            if item_context:
                context_parts.append(item_context)
            sources.extend(item_sources)
        return "\n\n".join(context_parts).strip(), _dedupe_strings(sources)

    content = getattr(result, "page_content", None) or getattr(result, "content", None) or getattr(result, "text", None)
    metadata = getattr(result, "metadata", {}) or {}
    sources = _normalize_sources(metadata.get("source") or metadata.get("file_path") or metadata.get("path") or [])
    return str(content or "").strip(), sources


def _normalize_sources(raw_sources: Any) -> List[str]:
    if raw_sources in (None, "", []):
        return []
    if isinstance(raw_sources, str):
        return [raw_sources]
    if isinstance(raw_sources, dict):
        return [str(raw_sources.get("source") or raw_sources.get("path") or raw_sources)]
    if isinstance(raw_sources, list):
        sources: List[str] = []
        for source in raw_sources:
            if isinstance(source, dict):
                sources.append(str(source.get("source") or source.get("path") or source))
            else:
                sources.append(str(source))
        return _dedupe_strings(sources)
    return [str(raw_sources)]


def _dedupe_strings(values: List[str]) -> List[str]:
    seen = set()
    result = []
    for value in values:
        cleaned = str(value).strip()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            result.append(cleaned)
    return result


def _detect_service_need(text: str, business_profile: Dict[str, Any]) -> str:
    normalized_text = _normalize_text(text)
    custom_services = _normalize_services(business_profile.get("services", []))

    for service in custom_services:
        service_text = _normalize_text(str(service))
        if service_text and service_text in normalized_text:
            return str(service)

    for service, keywords in SERVICE_KEYWORDS.items():
        if any(keyword in normalized_text for keyword in keywords):
            return service

    for service in custom_services:
        service_text = _normalize_text(str(service))
        if _shared_keyword_score(service_text, normalized_text) > 0:
            return str(service)

    return ""


def _detect_time(text: str) -> str:
    text = _normalize_text(text)
    patterns = [
        r"(今天|明天|后天|周末|这周末|本周末|这周|下周|下周[一二三四五六日天]?|周[一二三四五六日天])(?:上午|下午|晚上|中午|早上)?(?:\d{1,2}\s*点(?:半)?(?:到|-)?\d{0,2}\s*点?)?",
        r"\d{1,2}\s*月\s*\d{1,2}\s*[日号](?:上午|下午|晚上|中午|早上)?(?:\d{1,2}\s*点(?:半)?)?",
        r"(?:上午|下午|晚上|中午|早上)\s*\d{1,2}\s*点(?:半)?(?:到|-)?\d{0,2}\s*点?",
        r"\d{1,2}\s*点(?:半)?(?:到|-)?\d{0,2}\s*点?",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return _clean_extracted_text(match.group(0))
    return ""


def _detect_address(text: str) -> str:
    clean_text = _strip_noise_for_address(text)
    patterns = [
        r"(?:地址|位置|在|住在|我在|我住)[：:\s]*([\u4e00-\u9fa5A-Za-z0-9号楼栋单元室区县市镇街道路巷弄小区花园公寓大厦 -]{3,50})",
        r"([\u4e00-\u9fa5A-Za-z0-9]{2,20}(?:区|县|市|镇|街道|小区|花园|公寓|大厦|路|街|巷|弄)[\u4e00-\u9fa5A-Za-z0-9号楼栋单元室 -]{0,30})",
    ]
    for pattern in patterns:
        match = re.search(pattern, clean_text)
        if match:
            address = match.group(1 if match.lastindex else 0)
            return _clean_address(address)
    return ""


def _detect_budget(text: str) -> str:
    text_without_phone = re.sub(r"(?<!\d)1[3-9]\d{9}(?!\d)", " ", text)
    match = re.search(r"(\d{2,6}\s*(?:元|块|左右|以内|以下|以上)(?:\s*[-到]\s*\d{2,6}\s*元?)?)", text_without_phone)
    return match.group(1) if match else ""


def _extract_phone(text: str) -> str:
    match = re.search(r"(?<!\d)(1[3-9]\d{9})(?!\d)", text)
    if match:
        return match.group(1)
    match = re.search(r"(?<!\d)(?:\+?\d{1,4}[-\s]?)?\d{3,4}[-\s]?\d{6,8}(?!\d)", text)
    return match.group(0) if match else ""


def _default_price_for_service(service_need: str) -> str:
    if "保洁" in service_need:
        return "按面积和清洁难度估算，常见区间约 300-800 元"
    if "水管" in service_need or "维修" in service_need:
        return "上门检测费约 50-100 元，普通维修约 150-400 元"
    if "电路" in service_need:
        return "上门检测费约 50-100 元，普通维修约 150-500 元"
    if "锁" in service_need:
        return "普通开锁或换锁约 100-400 元"
    return "需根据服务内容、地址和时间进一步确认"


def _select_relevant_pricing(service_need: str, pricing_rules: Any) -> str:
    if isinstance(pricing_rules, dict):
        direct = _lookup_pricing_dict(service_need, pricing_rules)
        if direct:
            return direct
        return ""

    if isinstance(pricing_rules, list):
        candidates = [str(item) for item in pricing_rules if _pricing_matches_service(service_need, str(item))]
        return "；".join(candidates[:2])

    pricing_text = str(pricing_rules).strip()
    if not pricing_text:
        return ""

    parts = [part.strip() for part in re.split(r"[；;\n]", pricing_text) if part.strip()]
    candidates = [part for part in parts if _pricing_matches_service(service_need, part)]
    if candidates:
        return "；".join(candidates[:2])

    if len(parts) == 1 and len(parts[0]) <= 60:
        return parts[0]

    return ""


def _select_pricing_from_retrieved_context(service_need: str, state: FrontdeskState) -> str:
    context = state.get("retrieved_context", "")
    sources = state.get("retrieved_sources", [])
    if not context or not _has_pricing_source(sources):
        return ""

    parts = [part.strip() for part in re.split(r"[；;\n]", context) if part.strip()]
    candidates = [part for part in parts if _pricing_matches_service(service_need, part)]
    if candidates:
        return "；".join(candidates[:2])

    if _pricing_matches_service(service_need, context) and len(context) <= 120:
        return context.strip()

    return ""


def _is_knowledge_query(query: str) -> bool:
    knowledge_keywords = [
        "地址",
        "在哪",
        "哪里",
        "位置",
        "公司",
        "电话",
        "客服",
        "营业",
        "几点",
        "服务区域",
        "多少钱",
        "价格",
        "报价",
        "收费",
        "费用",
        "师傅",
        "员工",
        "人员",
        "保修",
        "售后",
        "复查",
    ]
    return any(keyword in query for keyword in knowledge_keywords)


def _find_context_line(context: str, keywords: list[str]) -> str:
    for line in _context_lines(context):
        if any(keyword in line for keyword in keywords):
            return line
    return ""


def _find_price_line(context: str, service_hint: str) -> str:
    lines = _context_lines(context)
    normalized_hint = _normalize_text(service_hint)
    for line in lines:
        normalized_line = _normalize_text(line)
        if "参考价" in line and (
            not normalized_hint or _shared_keyword_score(normalized_hint, normalized_line) > 0
        ):
            return line
    for line in lines:
        if any(token in line for token in ["元/平方米", "元起", "检测费", "参考价格"]):
            if not normalized_hint or _shared_keyword_score(normalized_hint, _normalize_text(line)) > 0:
                return line
    for line in lines:
        if any(token in line for token in ["元/平方米", "元起", "检测费", "参考价格"]):
            return line
    return ""


def _first_informative_context_line(context: str) -> str:
    for line in _context_lines(context):
        if len(line) >= 8 and not line.startswith("#") and not line.startswith("|---"):
            return line
    return ""


def _context_lines(context: str) -> list[str]:
    lines = []
    for raw_line in context.splitlines():
        line = raw_line.strip().strip("-").strip()
        if not line or line.startswith("#"):
            continue
        lines.append(line)
    return lines


def _clean_context_line(line: str) -> str:
    line = line.strip().strip("-").strip()
    line = re.sub(r"\s+", " ", line)
    return line.rstrip("。")


def _format_source_hint(sources: List[str]) -> str:
    if not sources:
        return "。"
    names = []
    for source in sources[:2]:
        name = str(source).replace("\\", "/").split("/")[-1]
        if name and name not in names:
            names.append(name)
    return f"。（资料来源：{'、'.join(names)}）" if names else "。"


def _has_pricing_source(sources: List[str]) -> bool:
    return any("pricing.md" in str(source).replace("\\", "/").lower() for source in sources)


def _lookup_pricing_dict(service_need: str, pricing_rules: Dict[Any, Any]) -> str:
    normalized_service = _normalize_text(service_need)
    for key, value in pricing_rules.items():
        normalized_key = _normalize_text(str(key))
        if normalized_key and (normalized_key in normalized_service or normalized_service in normalized_key):
            return _stringify_pricing_value(value)

    for key, value in pricing_rules.items():
        if _pricing_matches_service(service_need, str(key)):
            return _stringify_pricing_value(value)
    return ""


def _stringify_pricing_value(value: Any) -> str:
    if isinstance(value, list):
        return "；".join(str(item) for item in value)
    if isinstance(value, dict):
        return "；".join(f"{key}: {item}" for key, item in value.items())
    return str(value).strip()


def _pricing_matches_service(service_need: str, text: str) -> bool:
    normalized_service = _normalize_text(service_need)
    normalized_text = _normalize_text(text)
    if normalized_service and normalized_service in normalized_text:
        return True

    keywords = SERVICE_KEYWORDS.get(service_need, [])
    if any(keyword in normalized_text for keyword in keywords):
        return True

    return _shared_keyword_score(normalized_service, normalized_text) > 0


def _shared_keyword_score(service_text: str, target_text: str) -> int:
    tokens = [token for token in re.split(r"[,\s/|、，；;]+", service_text) if len(token) >= 2]
    score = 0
    for token in tokens:
        if token in target_text:
            score += 1
    return score


def _normalize_services(services: Any) -> List[str]:
    if isinstance(services, str):
        return [part.strip() for part in re.split(r"[,，、\n;；]", services) if part.strip()]
    if isinstance(services, list):
        return [str(item).strip() for item in services if str(item).strip()]
    return []


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", "", str(text))


def _strip_noise_for_address(text: str) -> str:
    text = re.sub(r"(?<!\d)1[3-9]\d{9}(?!\d)", " ", text)
    text = re.sub(r"(今天|明天|后天|周末|这周末|本周末|这周|下周|周[一二三四五六日天])(?:上午|下午|晚上|中午|早上)?(?:\d{1,2}\s*点(?:半)?)?", " ", text)
    text = re.sub(r"(电话|手机|联系)[：:\s]*", " ", text)
    return text


def _clean_address(address: str) -> str:
    address = _clean_extracted_text(address)
    address = re.sub(r"^(在|住在|我在|我住|地址|位置)[：:\s]*", "", address)
    address = re.split(r"[，。,.\n]|电话|手机|联系|明天|今天|后天|周末|上午|下午|晚上", address)[0]
    return address.strip(" ，。,.；;")


def _clean_extracted_text(text: str) -> str:
    return re.sub(r"\s+", "", str(text)).strip(" ，。,.；;")


def _extract_area_hint(text: str) -> str:
    match = re.search(r"(\d{1,4}\s*(?:平|平方|平方米|㎡))", text)
    return _clean_extracted_text(match.group(1)) if match else ""


def _normalize_lead(lead: Optional[Any]) -> Dict[str, Any]:
    data = _to_dict(lead)
    return {key: value for key, value in data.items() if value not in (None, "")}


def _to_dict(value: Any) -> Dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return deepcopy(value)
    if hasattr(value, "model_dump"):
        return value.model_dump()
    if hasattr(value, "dict"):
        return value.dict()
    return {}


def _safe_json_dict(text: str) -> Optional[Dict[str, Any]]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, flags=re.S)
        if not match:
            return None
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            return None

    if not isinstance(data, dict):
        return None

    return {field: data.get(field, "") for field in ALL_LEAD_FIELDS if field in data}


def _message_content(response: Any) -> str:
    return str(getattr(response, "content", response))


def _has_value(value: Any) -> bool:
    return value not in (None, "", [], {})


def _make_lead_id() -> str:
    return datetime.now().strftime("lead_%Y%m%d%H%M%S%f")


def _build_summary(lead: Dict[str, Any]) -> str:
    parts = []
    if lead.get("service_need"):
        parts.append(f"需求：{lead['service_need']}")
    if lead.get("preferred_time"):
        parts.append(f"时间：{lead['preferred_time']}")
    if lead.get("address"):
        parts.append(f"地址：{lead['address']}")
    if lead.get("urgency"):
        parts.append(f"紧急程度：{lead['urgency']}")
    return "；".join(parts)
