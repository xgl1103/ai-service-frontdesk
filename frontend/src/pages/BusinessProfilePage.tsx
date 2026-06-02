import { FormEvent, useEffect, useState } from "react";
import { Save } from "lucide-react";
import * as clientModule from "../api/client";
import "../styles/admin.css";

type Profile = {
  business_name?: string;
  industry?: string;
  service_area?: string;
  business_hours?: string;
  services?: string[] | string;
  pricing_rules?: Record<string, string> | string[] | string;
  faq?: Array<Record<string, string> | string> | string;
};

async function requestJson<T>(path: string, init?: RequestInit): Promise<T> {
  const module = clientModule as Record<string, any>;
  const client = module.apiClient ?? module.api ?? module.client ?? module.default;
  if (typeof module.request === "function") return module.request(path, init);
  if (client?.request) return client.request(path, init);
  if (!init?.method && client?.get) return client.get(path);
  if (init?.method === "PUT" && client?.put) return client.put(path, init.body ? JSON.parse(String(init.body)) : undefined);
  const baseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
  const response = await fetch(`${baseUrl}${path}`, init);
  if (!response.ok) throw new Error(`请求失败：${response.status}`);
  return response.json();
}

function textValue(value: unknown) {
  if (Array.isArray(value)) return value.map((item) => typeof item === "string" ? item : JSON.stringify(item)).join("\n");
  if (typeof value === "object" && value) return Object.entries(value).map(([key, item]) => `${key}: ${item}`).join("\n");
  return String(value ?? "");
}

export default function BusinessProfilePage() {
  const [form, setForm] = useState<Record<string, string>>({});
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    void requestJson<Profile>("/api/business-profile")
      .then((profile) => setForm({
        business_name: profile.business_name ?? "",
        industry: profile.industry ?? "",
        service_area: profile.service_area ?? "",
        business_hours: profile.business_hours ?? "",
        services: textValue(profile.services),
        pricing_rules: textValue(profile.pricing_rules),
        faq: textValue(profile.faq),
      }))
      .catch((reason) => setMessage(reason instanceof Error ? reason.message : "商家资料读取失败"));
  }, []);

  const update = (key: string, value: string) => setForm((current) => ({ ...current, [key]: value }));

  const save = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setMessage("");
    try {
      await requestJson("/api/business-profile", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...form,
          services: form.services.split("\n").map((item) => item.trim()).filter(Boolean),
        }),
      });
      setMessage("商家资料已保存。");
    } catch (reason) {
      setMessage(reason instanceof Error ? reason.message : "保存失败");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="admin-page">
      <header className="admin-page-header">
        <div>
          <p className="admin-eyebrow">基础配置</p>
          <h1>商家资料</h1>
          <p>维护前台答复需要的商家基础信息。知识库文档仍由运营单独维护。</p>
        </div>
      </header>

      {message && <p className="admin-alert">{message}</p>}
      <form className="admin-form" onSubmit={save}>
        <div className="form-grid">
          <label><span>商家名称</span><input value={form.business_name ?? ""} onChange={(event) => update("business_name", event.target.value)} /></label>
          <label><span>服务行业</span><input value={form.industry ?? ""} onChange={(event) => update("industry", event.target.value)} /></label>
          <label><span>服务区域</span><input value={form.service_area ?? ""} onChange={(event) => update("service_area", event.target.value)} /></label>
          <label><span>营业时间</span><input value={form.business_hours ?? ""} onChange={(event) => update("business_hours", event.target.value)} /></label>
        </div>
        <label><span>服务项目 <small>每行一项</small></span><textarea rows={6} value={form.services ?? ""} onChange={(event) => update("services", event.target.value)} /></label>
        <label><span>默认价格规则</span><textarea rows={7} value={form.pricing_rules ?? ""} onChange={(event) => update("pricing_rules", event.target.value)} /></label>
        <label><span>FAQ</span><textarea rows={7} value={form.faq ?? ""} onChange={(event) => update("faq", event.target.value)} /></label>
        <div className="form-actions">
          <button className="admin-button primary" disabled={busy} type="submit"><Save size={16} />保存资料</button>
        </div>
      </form>
    </section>
  );
}
