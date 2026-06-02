import { useEffect, useState } from "react";
import { BookOpen, FileText, RefreshCw, Search } from "lucide-react";
import * as clientModule from "../api/client";
import "../styles/admin.css";

type KnowledgeStatus = {
  index_exists?: boolean;
  embedding_provider?: string;
  chunk_count?: number;
  source_count?: number;
  index_file?: string;
  local_embedding_available?: boolean;
  openai_embedding_available?: boolean;
};

type SearchHit = { source: string; title: string; content: string; score: number };
type KnowledgeFile = { filename: string; source: string; size: number };

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const module = clientModule as Record<string, any>;
  const client = module.apiClient ?? module.api ?? module.client ?? module.default;
  if (typeof module.request === "function") return module.request(path, init);
  if (client?.request) return client.request(path, init);
  if (!init?.method && client?.get) return client.get(path);
  if (init?.method === "POST" && client?.post) return client.post(path, init.body ? JSON.parse(String(init.body)) : undefined);
  const baseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
  const response = await fetch(`${baseUrl}${path}`, init);
  if (!response.ok) throw new Error(`请求失败：${response.status}`);
  return response.json();
}

export default function KnowledgeBasePage() {
  const [status, setStatus] = useState<KnowledgeStatus>({});
  const [files, setFiles] = useState<KnowledgeFile[]>([]);
  const [selectedFile, setSelectedFile] = useState("");
  const [preview, setPreview] = useState("");
  const [query, setQuery] = useState("维修后保修多久？");
  const [hits, setHits] = useState<SearchHit[]>([]);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  const loadBaseData = async () => {
    setBusy(true);
    setMessage("");
    try {
      const [statusResult, fileResult] = await Promise.all([
        requestJson<KnowledgeStatus>("/api/knowledge/status"),
        requestJson<{ items: KnowledgeFile[] }>("/api/knowledge/files"),
      ]);
      const nextFiles = fileResult.items ?? [];
      setStatus(statusResult);
      setFiles(nextFiles);
      if (!selectedFile && nextFiles.length) setSelectedFile(nextFiles[0].filename);
    } catch (reason) {
      setMessage(reason instanceof Error ? reason.message : "知识库读取失败");
    } finally {
      setBusy(false);
    }
  };

  useEffect(() => {
    void loadBaseData();
  }, []);

  useEffect(() => {
    if (!selectedFile) return;
    void requestJson<{ content?: string } | string>(`/api/knowledge/files/${encodeURIComponent(selectedFile)}`)
      .then((result) => setPreview(typeof result === "string" ? result : result.content ?? ""))
      .catch((reason) => setMessage(reason instanceof Error ? reason.message : "文档预览失败"));
  }, [selectedFile]);

  const rebuild = async () => {
    setBusy(true);
    setMessage("");
    try {
      await requestJson("/api/knowledge/rebuild", { method: "POST" });
      setMessage("索引已重建。");
      await loadBaseData();
    } catch (reason) {
      setMessage(reason instanceof Error ? reason.message : "索引重建失败");
    } finally {
      setBusy(false);
    }
  };

  const search = async () => {
    if (!query.trim()) return;
    setBusy(true);
    setMessage("");
    try {
      const result = await requestJson<{ items: SearchHit[] }>("/api/knowledge/search", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query, top_k: 4 }),
      });
      setHits(result.items ?? []);
    } catch (reason) {
      setMessage(reason instanceof Error ? reason.message : "检索失败");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="admin-page">
      <header className="admin-page-header">
        <div>
          <p className="admin-eyebrow">运营维护</p>
          <h1>知识库管理</h1>
          <p>查看企业资料、维护索引，并快速验证检索质量。</p>
        </div>
        <button className="admin-button secondary" disabled={busy} onClick={() => void rebuild()} type="button">
          <RefreshCw size={16} />重建索引
        </button>
      </header>

      {message && <p className="admin-alert">{message}</p>}
      <div className="stat-grid">
        <div><span>索引状态</span><strong>{status.index_exists ? "可用" : "未构建"}</strong></div>
        <div><span>Markdown 文件</span><strong>{status.source_count ?? files.length}</strong></div>
        <div><span>知识片段</span><strong>{status.chunk_count ?? 0}</strong></div>
        <div><span>检索策略</span><strong>{status.embedding_provider ?? "-"}</strong></div>
      </div>
      <p className="admin-muted">本地 Embedding：{status.local_embedding_available ? "可用" : "未启用"} · OpenAI Embedding：{status.openai_embedding_available ? "可用" : "未启用"} · 索引：{status.index_file ?? "-"}</p>

      <div className="knowledge-layout">
        <aside className="admin-panel knowledge-files">
          <div className="panel-heading"><BookOpen size={16} /><strong>Markdown 文档</strong></div>
          {files.map((file) => (
            <button className={file.filename === selectedFile ? "file-button active" : "file-button"} key={file.filename} onClick={() => setSelectedFile(file.filename)} type="button">
              <FileText size={15} />{file.source}
            </button>
          ))}
          {!files.length && <p className="admin-empty compact">暂无文档。</p>}
        </aside>
        <article className="admin-panel preview-panel">
          <div className="panel-heading"><FileText size={16} /><strong>{selectedFile || "文档预览"}</strong></div>
          <pre>{preview || "选择左侧文档后查看内容。"}</pre>
        </article>
      </div>

      <section className="admin-panel search-panel">
        <div className="panel-heading"><Search size={16} /><strong>测试检索</strong></div>
        <div className="admin-inline-form">
          <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="输入测试问题" />
          <button className="admin-button primary" disabled={busy} onClick={() => void search()} type="button"><Search size={16} />检索</button>
        </div>
        <div className="hit-list">
          {hits.map((hit, index) => (
            <article className="search-hit" key={`${hit.source}-${index}`}>
              <div><strong>{hit.title || "未命名片段"}</strong><span>{hit.score.toFixed(4)}</span></div>
              <small>{hit.source}</small>
              <p>{hit.content}</p>
            </article>
          ))}
          {!hits.length && <p className="admin-empty compact">输入问题后查看命中片段。</p>}
        </div>
      </section>
    </section>
  );
}
