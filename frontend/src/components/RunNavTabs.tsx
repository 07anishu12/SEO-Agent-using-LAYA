"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, Lightbulb, Layers, FileCode, BarChart3 } from "lucide-react";

export default function RunNavTabs({ runId }: { runId: string }) {
  const pathname = usePathname();

  const tabs = [
    {
      href: `/runs/${runId}`,
      label: "Overview & Telemetry",
      icon: Activity,
      exact: true,
    },
    {
      href: `/runs/${runId}/opportunities`,
      label: "Opportunities",
      icon: Lightbulb,
      exact: false,
    },
    {
      href: `/runs/${runId}/templates`,
      label: "Templates",
      icon: Layers,
      exact: false,
    },
    {
      href: `/runs/${runId}/blueprints`,
      label: "Blueprints",
      icon: FileCode,
      exact: false,
    },
    {
      href: `/runs/${runId}/gsc`,
      label: "Query / GSC",
      icon: BarChart3,
      exact: false,
    },
  ];

  return (
    <div className="border-b border-slate-800">
      <nav className="flex space-x-2 overflow-x-auto pb-1" aria-label="Run tabs">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = tab.exact
            ? pathname === tab.href
            : pathname.startsWith(tab.href);

          return (
            <Link
              key={tab.href}
              href={tab.href}
              className={`flex items-center space-x-2 py-2 px-3.5 rounded-lg text-xs font-semibold whitespace-nowrap transition ${
                isActive
                  ? "bg-sky-500/10 text-sky-400 border border-sky-500/30 shadow-sm"
                  : "text-slate-400 hover:text-white hover:bg-slate-800/60"
              }`}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{tab.label}</span>
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
