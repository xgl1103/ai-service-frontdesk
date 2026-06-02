import { useEffect, useMemo, useState } from "react";
import { RefreshCw, Search, Trash2 } from "lucide-react";
import * as clientModule from "../api/client";
import "../styles/admin.css";

type Lead = {
  id?: string;
  status?: string;
  service_need?: string;
  phone?: string;
  address?: string;
  preferred_time?: string;
  urgency?: string;
  quote?: string | Record<string, unknown>;
  updated_at?: string;
};

const statusLabels: Record<string, string> = {
  new: "新线索",
  needs_info: "待补充信息",
  quoted: "已生成报价",
  handoff_required: "需人工接管",
  closed: "已关闭",
};

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const module = clientModule as Record<string, any>;
  const client = module.apiClient ?? module.api ?? module.client ?? module.default;
  if (typeof module.request === "function") return module.request(path, init);
  if (client?.request) return client.request(path, init);
  if (!init?.method && client?.get) return client.get(path);
  if (init?.method === "DELETE" && client?.delete) return client.delete(path);
  const baseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
  const response = await fetch(`${baseUrl}${path}`, init);
  if (!response.ok) throw new Error(`请求失败：${response.status}`);
  return response.json();
}

function quoteText(quote: Lead["quote"]) {
  if (!quote) return "-";
  return typeof quote === "string" ? quote : JSON.stringify(quote);
}

export default function LeadsBoardPage() {
  const [items, setItems] = useState<Lead[]>([]);
  const [status, setStatus] = useState("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadLeads = async () => {
    setLoading(true);
    setError("");
    try {
      const result = await requestJson<{ items: Lead[] }>("/api/leads");
      setItems(result.items ?? []);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "线索读取失败");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void loadLeads();
  }, []);

  const filteredItems = useMemo(
    () => (status === "all" ? items : items.filter((item) => item.status === status)),
    [items, status],
  );

  const clearLeads = async () => {
    if (!window.confirm("确定清空全部历史线索吗？此操作不可撤销。")) return;
    setError("");
    try {
      await requestJson("/api/leads", { method: "DELETE" });
      setItems([]);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "清空失败");
    }
  };

  return (
    <section className="admin-page">
      <header className="admin-page-header">
        <div>
          <p className="admin-eyebrow">客户跟进</p>
          <h1>线索看板</h1>
          <p>集中查看询盘、报价和需要人工介入的客户。</p>
        </div>
        <div className="admin-actions">
          <button className="admin-button secondary" onClick={() => void loadLeads()} type="button">
            <RefreshCw size={16} />刷新
          </button>
          <button className="admin-button danger" onClick={() => void clearLeads()} type="button">
            <Trash2 size={16} />清空线索
          </button>
        </div>
      </header>

      <div className="admin-toolbar">
        <label className="admin-filter">
          <Search size={15} />
          <span>状态筛选</span>
          <select value={status} onChange={(event) => setStatus(event.target.value)}>
            <option value="all">全部状态</option>
            {Object.entries(statusLabels).map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </label>
        <span className="admin-count">{filteredItems.length} 条线索</span>
      </div>

      {error && <p className="admin-alert error">{error}</p>}
      <div className="admin-table-wrap">
        <table className="admin-table">
          <thead>
            <tr>
              <th>状态</th><th>需求</th><th>电话</th><th>地址</th><th>期望时间</th>
              <th>紧急程度</th><th className="quote-cell">报价</th><th>更新时间</th>
            </tr>
          </thead>
          <tbody>
            {!loading && filteredItems.map((lead, index) => (
              <tr key={lead.id ?? `${lead.phone}-${index}`}>
                <td><span className={`status-badge ${lead.status ?? "new"}`}>{statusLabels[lead.status ?? "new"] ?? lead.status}</span></td>
                <td>{lead.service_need || "-"}</td>
                <td>{lead.phone || "-"}</td>
                <td>{lead.address || "-"}</td>
                <td>{lead.preferred_time || "-"}</td>
                <td>{lead.urgency || "-"}</td>
                <td className="quote-cell">{quoteText(lead.quote)}</td>
                <td>{lead.updated_at || "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {loading && <p className="admin-empty">正在读取线索...</p>}
        {!loading && !filteredItems.length && <p className="admin-empty">当前筛选条件下暂无线索。</p>}
      </div>
    </section>
  );
}
