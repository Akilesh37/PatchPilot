"use client";

import React from "react";
import {
  LayoutDashboard,
  Code2,
  ListTodo,
  FileDiff,
  Terminal,
  History,
  FolderGit2,
  ShieldCheck,
} from "lucide-react";
import { Migration } from "../../lib/api";

export type NavTab =
  | "overview"
  | "analysis"
  | "planner"
  | "review"
  | "verification"
  | "history";

interface SidebarNavigationProps {
  activeTab: NavTab;
  onTabChange: (tab: NavTab) => void;
  currentMigration: Migration | null;
  repoPath: string;
}

interface NavItem {
  id: NavTab;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  badge?: string | number;
}

export function SidebarNavigation({
  activeTab,
  onTabChange,
  currentMigration,
  repoPath,
}: SidebarNavigationProps) {
  const shortRepoName = repoPath.split("/").pop() || repoPath;

  const changedFilesCount = currentMigration?.patch?.changed_files_count;
  const plannedOpsCount = currentMigration?.plan?.applicable_rule_ids?.length;
  const verificationRun = currentMigration?.verification_runs?.[0];

  const navItems: NavItem[] = [
    {
      id: "overview",
      label: "Overview",
      icon: LayoutDashboard,
    },
    {
      id: "analysis",
      label: "Repository Analysis",
      icon: Code2,
    },
    {
      id: "planner",
      label: "Migration Planner",
      icon: ListTodo,
      badge: plannedOpsCount ? `${plannedOpsCount} ops` : undefined,
    },
    {
      id: "review",
      label: "Code Review & Diffs",
      icon: FileDiff,
      badge: changedFilesCount ? `${changedFilesCount} files` : undefined,
    },
    {
      id: "verification",
      label: "Verification & Sandbox",
      icon: Terminal,
      badge: verificationRun
        ? verificationRun.status === "PASSED"
          ? "Passed"
          : "Check"
        : undefined,
    },
    {
      id: "history",
      label: "History & Rollback",
      icon: History,
    },
  ];

  return (
    <aside className="w-64 bg-[#0e1117] border-r border-slate-800/80 flex flex-col shrink-0 select-none">
      {/* Workspace Context Section */}
      <div className="p-3.5 border-b border-slate-800/80">
        <div className="flex items-center gap-2.5 px-2 py-1.5 rounded-md bg-slate-900/60 border border-slate-800/60">
          <FolderGit2 className="w-4 h-4 text-blue-400 shrink-0" />
          <div className="min-w-0 flex-1">
            <span className="text-[10px] font-mono uppercase tracking-wider text-slate-500 block">
              Active Repository
            </span>
            <span className="text-xs font-mono font-medium text-slate-200 truncate block">
              {shortRepoName}
            </span>
          </div>
        </div>
      </div>

      {/* Navigation Links (NO NUMBERED LABELS) */}
      <div className="p-2 space-y-0.5 flex-1 overflow-y-auto">
        <div className="px-2.5 py-1.5 text-[10px] font-mono uppercase tracking-wider text-slate-500 font-semibold">
          Platform Console
        </div>

        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;

          return (
            <button
              key={item.id}
              onClick={() => onTabChange(item.id)}
              className={`w-full flex items-center justify-between px-3 py-2 rounded-md text-xs font-medium transition-colors cursor-pointer group ${
                isActive
                  ? "bg-blue-600/10 text-blue-400 font-semibold border-l-2 border-blue-500 rounded-l-none"
                  : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/50"
              }`}
            >
              <div className="flex items-center gap-2.5 min-w-0">
                <Icon
                  className={`w-4 h-4 shrink-0 transition-colors ${
                    isActive ? "text-blue-400" : "text-slate-500 group-hover:text-slate-300"
                  }`}
                />
                <span className="truncate">{item.label}</span>
              </div>

              {item.badge && (
                <span
                  className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${
                    isActive
                      ? "bg-blue-500/20 text-blue-300"
                      : "bg-slate-800 text-slate-400 group-hover:text-slate-300"
                  }`}
                >
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Bottom Footer Info */}
      <div className="p-3 border-t border-slate-800/80 space-y-2.5">
        {/* Sandbox Status Panel */}
        <div className="p-2.5 rounded-md bg-slate-900/60 border border-slate-800/60 space-y-1.5">
          <div className="flex items-center justify-between text-[11px]">
            <span className="text-slate-400 flex items-center gap-1.5">
              <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
              <span>Sandbox Tier</span>
            </span>
            <span className="font-mono text-[10px] text-emerald-400 font-medium">Tier 2</span>
          </div>
          <p className="text-[10px] text-slate-500 leading-tight">
            Hardened host subprocess with process group isolation and secret scrubbing.
          </p>
        </div>

        {/* System Link Status */}
        <div className="flex items-center justify-between px-2 text-[10px] text-slate-500 font-mono">
          <span className="flex items-center gap-1.5">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
            FastAPI 8000
          </span>
          <span>Next.js 3000</span>
        </div>
      </div>
    </aside>
  );
}
