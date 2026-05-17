import { Link, useLocation } from "react-router-dom";
import { Moon, Search, Sun, Bell, ChevronRight } from "lucide-react";
import { useTheme } from "@/lib/theme";

const titles: Record<string, string> = {
  dashboard: "Dashboard",
  pipelines: "Pipelines",
  connections: "Connections",
  jobs: "Job Runs",
  errors: "Error Explorer",
  settings: "Settings",
};

export function Header() {
  const { pathname } = useLocation();
  const { theme, toggle } = useTheme();
  const parts = pathname.split("/").filter(Boolean);
  const root = parts[0] || "dashboard";

  return (
    <header className="sticky top-0 z-10 flex h-14 items-center justify-between border-b border-zinc-200 bg-white/80 px-6 backdrop-blur dark:border-zinc-800 dark:bg-zinc-950/80">
      <nav className="flex items-center gap-2 text-[13px]">
        <Link
          to={`/${root}`}
          className="font-semibold text-zinc-900 dark:text-zinc-100"
        >
          {titles[root] ?? root}
        </Link>
        {parts.length > 1 && (
          <>
            <ChevronRight size={14} className="text-zinc-400" />
            <span className="font-mono text-zinc-500 truncate max-w-[280px]">
              {parts.slice(1).join(" / ")}
            </span>
          </>
        )}
      </nav>

      <div className="flex items-center gap-2">
        <div className="relative">
          <Search
            size={14}
            className="absolute left-2.5 top-1/2 -translate-y-1/2 text-zinc-400"
          />
          <input
            className="input pl-7 w-56"
            placeholder="Search..."
            aria-label="Search"
          />
        </div>
        <button
          onClick={toggle}
          className="btn-ghost h-7 w-7 p-0"
          aria-label="Toggle theme"
          title={theme === "dark" ? "Light mode" : "Dark mode"}
        >
          {theme === "dark" ? <Sun size={14} /> : <Moon size={14} />}
        </button>
        <button className="btn-ghost h-7 w-7 p-0" aria-label="Notifications">
          <Bell size={14} />
        </button>
        <div className="flex h-7 w-7 items-center justify-center rounded-full bg-bifrost-gradient text-[11px] font-semibold text-white">
          A
        </div>
      </div>
    </header>
  );
}
