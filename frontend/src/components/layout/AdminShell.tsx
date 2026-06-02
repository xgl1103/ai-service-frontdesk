import { BookOpen, ClipboardList, FlaskConical, Home, MessageCircle, Settings2 } from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";

const navItems = [
  { to: "/admin/leads", label: "线索看板", icon: ClipboardList },
  { to: "/admin/knowledge", label: "知识库", icon: BookOpen },
  { to: "/admin/profile", label: "商家资料", icon: Settings2 },
  { to: "/admin/test", label: "系统测试", icon: FlaskConical },
];

export function AdminShell() {
  return (
    <div className="admin-shell">
      <aside className="admin-sidebar">
        <div className="admin-brand">
          <strong>安心到家</strong>
          <span>服务后台</span>
        </div>
        <nav aria-label="商家后台导航">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink className={({ isActive }) => isActive ? "admin-nav-link active" : "admin-nav-link"} key={to} to={to}>
              <Icon size={17} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="admin-sidebar-footer">
          <NavLink className="admin-nav-link" to="/chat"><MessageCircle size={17} /><span>客户咨询页</span></NavLink>
          <NavLink className="admin-nav-link" to="/"><Home size={17} /><span>返回首页</span></NavLink>
        </div>
      </aside>
      <div className="admin-workspace">
        <Outlet />
      </div>
    </div>
  );
}
