"use client";

import React from "react";
import {
  Play,
  RotateCw,
  GitBranch,
  ShieldCheck,
  Terminal,
  ExternalLink,
  Layers,
} from "lucide-react";
import { StatusBadge } from "../ui/StatusBadge";
import { Migration } from "../../lib/api";

interface WorkspaceHeaderProps {
  currentMigration: Migration | null;
  repoPath: string;
  loading: boolean;
  onRunMigration: () => void;
  activeTab: string;
}

export function WorkspaceHeader({
  currentMigration,
  repoPath,
  loading,
  onRunMigration,
}: WorkspaceHeaderProps) {
  const shortRepoName = repoPath.split("/").pop() || repoPath;

  return (
    <header className="h-14 border-b border-slate-800/80 bg-[#0e1117] px-5 flex items-center justify-between sticky top-0 z-40 select-none">
      {/* Brand & Workspace Context */}
      <div className="flex items-center gap-4">
        {/* Logo */}
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-md bg-blue-600 flex items-center justify-center text-white shadow-sm shadow-blue-500/20">
            <Layers className="w-4 h-4 stroke-[2.2]" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold tracking-tight text-slate-100">
                PatchPilot
              </span>
              <span className="px-1.5 py-0.5 text-[10px] font-mono font-medium rounded bg-slate-800 text-slate-400 border border-slate-700/60">
                v1.0.0
              </span>
            </div>
          </div>
        </div>

        {/* Separator */}
        <div className="h-4 w-px bg-slate-800" />

        {/* Target Version & Framework Badge */}
        <div className="hidden sm:flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-mono font-medium rounded-md bg-slate-900 border border-slate-800 text-slate-300">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />
            Spring Boot 2.7 ➔ 3.2
          </span>
          <span className="text-[11px] font-mono text-slate-500">JDK 17 Baseline</span>
        </div>

        {/* Separator */}
        <div className="hidden md:block h-4 w-px bg-slate-800" />

        {/* Current Repository Target Pill */}
        <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1 text-xs font-mono rounded-md bg-slate-900/80 border border-slate-800/80 text-slate-400">
          <GitBranch className="w-3.5 h-3.5 text-slate-500" />
          <span className="text-slate-300 font-medium">{shortRepoName}</span>
        </div>
      </div>

      {/* Right Actions & Status */}
      <div className="flex items-center gap-3">
        {/* Sandbox Status Chip */}
        <div className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 text-[11px] font-mono rounded-md bg-slate-900 border border-slate-800 text-slate-400">
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
          <span className="text-slate-300">Sandbox:</span>
          <span className="text-emerald-400">Tier 2 Active</span>
        </div>

        {/* Active Migration Status */}
        {currentMigration && (
          <div className="flex items-center gap-2">
            <span className="text-[11px] font-mono text-slate-500 hidden xl:inline">Status:</span>
            <StatusBadge status={currentMigration.status} size="sm" />
          </div>
        )}

        {/* API Docs link */}
        <a
          href="http://127.0.0.1:8000/docs"
          target="_blank"
          rel="noreferrer"
          title="Open FastAPI Swagger Documentation"
          className="hidden sm:flex items-center gap-1 px-2.5 py-1.5 text-xs text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 rounded-md transition border border-transparent hover:border-slate-800"
        >
          <Terminal className="w-3.5 h-3.5" />
          <span>API Docs</span>
          <ExternalLink className="w-3 h-3 opacity-60" />
        </a>

        {/* Primary Action: Run Migration */}
        <button
          onClick={onRunMigration}
          disabled={loading}
          className="flex items-center gap-2 px-3.5 py-1.5 text-xs font-semibold rounded-md bg-blue-600 hover:bg-blue-500 text-white shadow-sm shadow-blue-600/30 transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed focus:outline-none focus:ring-2 focus:ring-blue-500/50"
        >
          {loading ? (
            <RotateCw className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <Play className="w-3.5 h-3.5 fill-current" />
          )}
          <span>{loading ? "Analyzing..." : "Run Migration"}</span>
        </button>
      </div>
    </header>
  );
}

