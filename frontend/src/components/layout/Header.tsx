import { useLocation } from "react-router-dom";
import { Bell, Search } from "lucide-react";

const titles: Record<string, string> = {
  dashboard: "Dashboard",
  connections: "Connections",
  pipelines: "Pipelines",
  jobs: "Job Runs",
  settings: "Settings",
};

export function Header() {
  const { pathname } = useLocation();
  const segment = pathname.split("/")[1] || "dashboard";
  const title = titles[segment] ?? segment;

  return (
    <header className="flex h-16 items-center justify-between border-b border-slate-200 bg-white px-8">
      <h1 className="text-lg font-semibold text-slate-900">{title}</h1>
      <div className="flex items-center gap-3">
        <div className="relative">
          <Search
            size={16}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
          />
          <input
            className="input pl-9 w-64"
            placeholder="Search..."
            aria-label="Search"
          />
        </div>
        <button className="btn-ghost h-9 w-9 p-0" aria-label="Notifications">
          <Bell size={18} />
        </button>
        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-brand-100 text-sm font-semibold text-brand-700">
          A
        </div>
      </div>
    </header>
  );
}
