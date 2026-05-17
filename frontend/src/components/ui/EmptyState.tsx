import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";

interface Props {
  icon: LucideIcon;
  title: string;
  description: string;
  action?: ReactNode;
}

export function EmptyState({ icon: Icon, title, description, action }: Props) {
  return (
    <div className="card flex flex-col items-center justify-center gap-3 px-6 py-16 text-center">
      <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-bifrost-gradient text-white">
        <Icon size={20} />
      </div>
      <div>
        <h3 className="text-sm font-semibold text-zinc-900 dark:text-zinc-100">
          {title}
        </h3>
        <p className="mt-1 text-xs text-zinc-500 dark:text-zinc-400">
          {description}
        </p>
      </div>
      {action}
    </div>
  );
}
