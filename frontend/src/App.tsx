import { ArrowRight, BookOpen, ClipboardList, FlaskConical, MessageCircle, Settings2 } from "lucide-react";
import { Link, Navigate, Route, Routes } from "react-router-dom";

import { AdminShell } from "./components/layout/AdminShell";
import BusinessProfilePage from "./pages/BusinessProfilePage";
import CustomerChatPage from "./pages/CustomerChatPage";
import KnowledgeBasePage from "./pages/KnowledgeBasePage";
import LeadsBoardPage from "./pages/LeadsBoardPage";
import SystemTestPage from "./pages/SystemTestPage";

const destinations = [
  { to: "/chat", label: "客户咨询", detail: "面向客户的 AI 前台入口", icon: MessageCircle },
  { to: "/admin/leads", label: "线索看板", detail: "集中查看询盘与人工接管事项", icon: ClipboardList },
  { to: "/admin/knowledge", label: "知识库管理", detail: "查看企业资料并测试检索", icon: BookOpen },
  { to: "/admin/profile", label: "商家资料", detail: "维护服务范围与基础配置", icon: Settings2 },
  { to: "/admin/test", label: "系统测试", detail: "检查回复、线索抽取与 RAG 来源", icon: FlaskConical },
];

function HomePage() {
  return (
    <main className="home-page">
      <div className="home-shell">
        <p className="home-eyebrow">AI SERVICE FRONTDESK</p>
        <h1>安心到家服务</h1>
        <p className="home-summary">从客户咨询到商家跟进，把服务资料、询盘线索和 AI 前台放在一个清晰的工作流里。</p>
        <div className="home-grid">
          {destinations.map(({ to, label, detail, icon: Icon }) => (
            <Link className="home-link" key={to} to={to}>
              <Icon size={18} />
              <span>
                <strong>{label}</strong>
                <small>{detail}</small>
              </span>
              <ArrowRight className="home-arrow" size={17} />
            </Link>
          ))}
        </div>
      </div>
    </main>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/chat" element={<CustomerChatPage />} />
      <Route path="/admin" element={<AdminShell />}>
        <Route index element={<Navigate replace to="/admin/leads" />} />
        <Route path="leads" element={<LeadsBoardPage />} />
        <Route path="knowledge" element={<KnowledgeBasePage />} />
        <Route path="profile" element={<BusinessProfilePage />} />
        <Route path="test" element={<SystemTestPage />} />
      </Route>
      <Route path="*" element={<Navigate replace to="/" />} />
    </Routes>
  );
}
