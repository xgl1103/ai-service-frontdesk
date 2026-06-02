import { FormEvent, useState } from "react";
import { Play, RotateCcw } from "lucide-react";
import * as clientModule from "../api/client";
import "../styles/admin.css";

type ChatResult = {
  assistant_reply?: string;
  lead?: Record<string, unknown>;
  missing_fields?: string[];
  quote?: string;
  handoff_required?: boolean;
  retrieved_sources?: string[];
  retrieved_context?: string;
};

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const module = clientModule as Record<string, any>;
  const client = module.apiClient ?? module.api ?? module.client ?? module.default;
  if (typeof module.request === "function") return module.request(path, init);
  if (client?.request) return client.request(path, init);
  if (init?.method === "POST" && client?.post) return client.post(path, init.body ? JSON.parse(String(init.body)) : undefined);
  const baseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
  const response = await fetch(`${baseUrl}${path}`, init);
  if (!response.ok) throw new Error(`请求失败：${response.status}`);
  return response.json();
}

export default function SystemTestPage() {
  const [question, setQuestion] = useState("我家厨房水管漏水，明天上午能来修吗？");
  const [currentLead, setCurrentLead] = useState<Record<string, unknown>>({});
  const [result, setResult] = useState<ChatResult | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const test = async (event: FormEvent) => {
    event.preventDefault();
    if (!question.trim()) return;
    setBusy(true);
    setError("");
    try {
      const nextResult = await requestJson<ChatResult>("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: question, current_lead: currentLead, chat_history: [] }),
      });
      setResult(nextResult);
      setCurrentLead(nextResult.lead ?? {});
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "测试请求失败");
    } finally {
      setBusy(false);
    }
  };

  const reset = () => {
    setCurrentLead({});
    setResult(null);
    setError("");
  };

  return (
    <section className="admin-page">
      <header className="admin-page-header">
        <div>
          <p className="admin-eyebrow">开发与运营</p>
          <h1>系统测试</h1>
          <p>检查 AI 回复、结构化线索、人工接管和 RAG 命中结果。</p>
        </div>
        <button className="admin-button secondary" onClick={reset} type="button"><RotateCcw size={16} />重置会话</button>
      </header>

      <form className="admin-panel test-form" onSubmit={test}>
        <label><span>测试问题</span><textarea rows={4} value={question} onChange={(event) => setQuestion(event.target.value)} /></label>
        <button className="admin-button primary" disabled={busy} type="submit"><Play size={16} />{busy ? "测试中..." : "运行测试"}</button>
      </form>
      {error && <p className="admin-alert error">{error}</p>}

      {result && (
        <div className="debug-grid">
          <section className="admin-panel debug-span">
            <div className="panel-heading"><strong>AI 回复</strong></div>
            <p className="reply-text">{result.assistant_reply || "-"}</p>
          </section>
          <section className="admin-panel">
            <div className="panel-heading"><strong>缺失字段</strong></div>
            <div className="tag-list">{result.missing_fields?.length ? result.missing_fields.map((field) => <span key={field}>{field}</span>) : <em>无</em>}</div>
          </section>
          <section className="admin-panel">
            <div className="panel-heading"><strong>人工接管</strong></div>
            <p><span className={`status-badge ${result.handoff_required ? "handoff_required" : "quoted"}`}>{result.handoff_required ? "需要人工接管" : "无需人工接管"}</span></p>
          </section>
          <section className="admin-panel debug-span">
            <div className="panel-heading"><strong>线索 JSON</strong></div>
            <pre>{JSON.stringify(result.lead ?? {}, null, 2)}</pre>
          </section>
          <section className="admin-panel debug-span">
            <div className="panel-heading"><strong>retrieved_sources</strong></div>
            <pre>{JSON.stringify(result.retrieved_sources ?? [], null, 2)}</pre>
          </section>
          <section className="admin-panel debug-span">
            <div className="panel-heading"><strong>retrieved_context</strong></div>
            <pre>{result.retrieved_context || "未命中检索资料"}</pre>
          </section>
        </div>
      )}
    </section>
  );
}
