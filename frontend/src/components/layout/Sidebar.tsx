import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  Plug,
  Workflow,
  Activity,
  Settings as SettingsIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";

const nav = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { to: "/connections", label: "Connections", icon: Plug },
  { to: "/pipelines", label: "Pipelines", icon: Workflow },
  { to: "/jobs", label: "Job Runs", icon: Activity },
  { to: "/settings", label: "Settings", icon: SettingsIcon },
];

export function Sidebar() {
  return (
    <aside className="flex w-60 flex-col border-r border-slate-200 bg-slate-950 text-slate-100">
      <div className="flex h-16 items-center gap-2 border-b border-slate-800 px-5">
        <div className="flex h-9 w-9 items-center justify-center rounded-md bg-brand-600 text-sm font-bold text-white">
          DIP
        </div>
        <div className="leading-tight">
          <div className="text-sm font-semibold">Data Integration</div>
          <div className="text-xs text-slate-400">Platform</div>
        </div>
      </div>
      <nav className="flex flex-1 flex-col gap-1 p-3">
        {nav.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-brand-600/90 text-white"
                  : "text-slate-300 hover:bg-slate-800/70 hover:text-white"
              )
            }
          >
            <item.icon size={18} />
            {item.label}
          </NavLink>
        ))}
      </nav>
      <div className="border-t border-slate-800 p-4 text-xs text-slate-400">
        <div>v0.1.0</div>
        <div className="mt-1">© DIP</div>
      </div>
    </aside>
  );
}
