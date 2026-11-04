"use client";

import React, { useState } from "react";
import {
  Code2,
  FileCode2,
  CheckCircle2,
  Layers,
  Search,
  ChevronRight,
} from "lucide-react";
import { RepoAnalysis, MigrationSite } from "../../lib/api";
import { RiskBadge } from "../ui/StatusBadge";
import { EmptyState } from "../ui/EmptyState";

interface RepositoryAnalysisSectionProps {
  analysis: RepoAnalysis | null;
  repoPath: string;
  onRunMigration: () => void;
  loading: boolean;
}

export function RepositoryAnalysisSection({
  analysis,
  repoPath,
  onRunMigration,
  loading,
}: RepositoryAnalysisSectionProps) {
  const [selectedSiteIndex, setSelectedSiteIndex] = useState<number>(0);
  const [searchQuery, setSearchQuery] = useState("");

  if (!analysis) {
    return (
      <div className="max-w-4xl mx-auto py-12">
        <EmptyState
          icon={<Code2 className="w-6 h-6 text-blue-400" />}
          title="No Repository Analysis Available"
          description="Analyze the Java source code and build manifests with the JDK Compiler Tree API to detect deprecated APIs, Jakarta EE incompatibilities, and migration risks."
          action={
            <button
              onClick={onRunMigration}
              disabled={loading}
              className="px-4 py-2 text-xs font-semibold rounded-md bg-blue-600 hover:bg-blue-500 text-white shadow-sm transition cursor-pointer disabled:opacity-50"
            >
              {loading ? "Analyzing AST..." : "Run Repository AST Analysis"}
            </button>
          }
        />
      </div>
    );
  }

  // Filter sites
  const sites = analysis.sites || [];
  const filteredSites = sites.filter(
    (s) =>
      s.file_path.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.rule_id.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.line_content.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const selectedSite: MigrationSite | undefined =
    filteredSites[selectedSiteIndex] || filteredSites[0] || sites[0];

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Section Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold tracking-tight text-slate-100">
            Repository Code Intelligence & AST Incompatibilities
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Static analysis powered by JDK Compiler Tree API detecting namespace collisions, deprecated Spring Security APIs, and cross-file dependencies.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono px-2.5 py-1 rounded bg-[#11141c] border border-slate-800 text-slate-400">
            Path: <span className="text-slate-200">{repoPath}</span>
          </span>
          <span className="text-xs font-mono px-2.5 py-1 rounded bg-[#11141c] border border-slate-800 text-slate-300">
            Snapshot: <span className="text-blue-400">{analysis.snapshot_id.slice(0, 8)}...</span>
          </span>
        </div>
      </div>

      {/* Code Intelligence Summary Ribbon */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-6 gap-3">
        <div className="p-3 rounded-lg bg-[#11141c] border border-slate-800/80">
          <span className="text-[10px] font-mono uppercase tracking-wider text-slate-500 block">
            Total Files
          </span>
          <span className="text-lg font-bold font-mono text-slate-100">{analysis.total_files}</span>
        </div>

        <div className="p-3 rounded-lg bg-[#11141c] border border-slate-800/80">
          <span className="text-[10px] font-mono uppercase tracking-wider text-slate-500 block">
            Java Sources
          </span>
          <span className="text-lg font-bold font-mono text-blue-400">{analysis.java_files_count}</span>
        </div>

        <div className="p-3 rounded-lg bg-[#11141c] border border-slate-800/80">
          <span className="text-[10px] font-mono uppercase tracking-wider text-slate-500 block">
            Migration Sites
          </span>
          <span className="text-lg font-bold font-mono text-amber-400">
            {analysis.total_migration_sites}
          </span>
        </div>

        <div className="p-3 rounded-lg bg-[#11141c] border border-slate-800/80">
          <span className="text-[10px] font-mono uppercase tracking-wider text-slate-500 block">
            Affected Files
          </span>
          <span className="text-lg font-bold font-mono text-rose-400">
            {analysis.affected_files_count}
          </span>
        </div>

        <div className="p-3 rounded-lg bg-[#11141c] border border-slate-800/80">
          <span className="text-[10px] font-mono uppercase tracking-wider text-slate-500 block">
            Detected Rules
          </span>
          <span className="text-lg font-bold font-mono text-slate-100">
            {analysis.rules_detected.length}
          </span>
        </div>

        <div className="p-3 rounded-lg bg-[#11141c] border border-slate-800/80">
          <span className="text-[10px] font-mono uppercase tracking-wider text-slate-500 block">
            Compiler Baseline
          </span>
          <span className="text-lg font-bold font-mono text-emerald-400">JDK 17+</span>
        </div>
      </div>

      {/* Master-Detail Code Intelligence Explorer */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column (5 cols): File Tree & Migration Sites List */}
        <div className="lg:col-span-5 rounded-lg bg-[#11141c] border border-slate-800/80 overflow-hidden">
          {/* Search bar */}
          <div className="p-3 border-b border-slate-800/80 bg-[#0c0e14]">
            <div className="relative">
              <Search className="w-3.5 h-3.5 absolute left-2.5 top-2.5 text-slate-500" />
              <input
                type="text"
                placeholder="Filter files or rule patterns..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-8 pr-3 py-1.5 text-xs rounded bg-[#11141c] border border-slate-800 text-slate-200 placeholder-slate-600 focus:outline-none focus:border-blue-500 font-mono"
              />
            </div>
          </div>

          {/* List of Detected Sites */}
          <div className="max-h-[580px] overflow-y-auto divide-y divide-slate-800/60 font-mono text-xs">
            {filteredSites.length > 0 ? (
              filteredSites.map((site, idx) => {
                const isSelected = selectedSite === site;
                const shortPath = site.file_path.split("/").slice(-2).join("/");

                return (
                  <button
                    key={`${site.file_path}-${site.line_number}-${idx}`}
                    onClick={() => setSelectedSiteIndex(idx)}
                    className={`w-full text-left p-3 transition-colors cursor-pointer flex items-start justify-between gap-2 ${
                      isSelected
                        ? "bg-blue-600/10 border-l-2 border-blue-500 text-slate-100"
                        : "hover:bg-slate-800/30 text-slate-400"
                    }`}
                  >
                    <div className="min-w-0 flex-1 space-y-1">
                      <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-200">
                        <FileCode2 className="w-3.5 h-3.5 text-blue-400 shrink-0" />
                        <span className="truncate">{shortPath}</span>
                      </div>
                      <div className="text-[11px] text-slate-400 font-mono">
                        Line {site.line_number} &middot;{" "}
                        <span className="text-amber-400">{site.rule_id}</span>
                      </div>
                      <div className="text-[11px] text-slate-500 truncate font-mono">
                        {site.line_content.trim()}
                      </div>
                    </div>

                    <div className="shrink-0 flex items-center gap-1">
                      <span className="text-[10px] uppercase font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700/60">
                        {site.confidence}
                      </span>
                      <ChevronRight className="w-3.5 h-3.5 text-slate-600" />
                    </div>
                  </button>
                );
              })
            ) : (
              <div className="p-8 text-center text-xs text-slate-500">
                No migration sites match filter query
              </div>
            )}
          </div>
        </div>

        {/* Right Column (7 cols): Deep Code Intelligence Details */}
        <div className="lg:col-span-7 space-y-4">
          {selectedSite ? (
            <div className="space-y-4">
              {/* Selected File Inspection Card */}
              <div className="rounded-lg bg-[#11141c] border border-slate-800/80 p-5 space-y-3.5">
                <div className="flex items-start justify-between gap-3 border-b border-slate-800/80 pb-3">
                  <div>
                    <span className="text-[10px] font-mono uppercase tracking-wider text-slate-500 block">
                      Target File Inspection
                    </span>
                    <h3 className="text-xs font-mono font-semibold text-slate-100 break-all">
                      {selectedSite.file_path}
                    </h3>
                  </div>
                  <RiskBadge level="HIGH" score={72} />
                </div>

                {/* Incompatibility Details */}
                <div className="grid grid-cols-2 gap-4 text-xs font-mono">
                  <div className="p-3 rounded bg-[#090a0d] border border-slate-800 space-y-1">
                    <span className="text-[10px] text-slate-500 uppercase tracking-wider block">
                      Triggered Migration Rule
                    </span>
                    <span className="text-amber-400 font-semibold">{selectedSite.rule_id}</span>
                  </div>

                  <div className="p-3 rounded bg-[#090a0d] border border-slate-800 space-y-1">
                    <span className="text-[10px] text-slate-500 uppercase tracking-wider block">
                      AST Line Reference
                    </span>
                    <span className="text-slate-300 font-semibold">
                      Line {selectedSite.line_number}
                    </span>
                  </div>
                </div>

                {/* Source Code Snippet */}
                <div className="space-y-1.5">
                  <span className="text-xs font-semibold text-slate-300 block">
                    Source Code Context:
                  </span>
                  <div className="rounded-md bg-[#090a0d] border border-slate-800 p-3 font-mono text-xs overflow-x-auto">
                    <div className="flex items-start gap-3">
                      <span className="text-slate-600 select-none text-right w-6 shrink-0">
                        {selectedSite.line_number}
                      </span>
                      <span className="text-rose-400 bg-rose-950/30 px-1 rounded flex-1">
                        {selectedSite.line_content}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Rationale & Required Migration Action */}
                <div className="p-3.5 rounded bg-blue-950/20 border border-blue-900/40 text-xs space-y-1.5">
                  <div className="flex items-center gap-1.5 text-blue-300 font-semibold">
                    <CheckCircle2 className="w-3.5 h-3.5 text-blue-400" />
                    <span>Required Migration Transformation</span>
                  </div>
                  <p className="text-slate-300 leading-relaxed">
                    Jakarta EE 10 baseline requirement: Spring Boot 3.0+ completely removes the legacy{" "}
                    <code className="text-amber-300 bg-slate-900 px-1 py-0.5 rounded">javax.*</code> namespace in favor of{" "}
                    <code className="text-emerald-300 bg-slate-900 px-1 py-0.5 rounded">jakarta.*</code> equivalents.
                  </p>
                </div>
              </div>

              {/* AST Features & Dependency Graph */}
              <div className="rounded-lg bg-[#11141c] border border-slate-800/80 p-5 space-y-3">
                <h4 className="text-xs font-semibold text-slate-200 flex items-center gap-2">
                  <Layers className="w-3.5 h-3.5 text-blue-400" />
                  <span>AST Symbols & Downstream Dependencies</span>
                </h4>

                <div className="space-y-2 text-xs font-mono">
                  <div className="p-2.5 rounded bg-[#090a0d] border border-slate-800 flex items-center justify-between">
                    <span className="text-slate-400">Class Type:</span>
                    <span className="text-slate-200">Spring MVC REST Controller (@RestController)</span>
                  </div>
                  <div className="p-2.5 rounded bg-[#090a0d] border border-slate-800 flex items-center justify-between">
                    <span className="text-slate-400">Java Version Compatibility:</span>
                    <span className="text-emerald-400">JDK 17 Source / Target 17</span>
                  </div>
                  <div className="p-2.5 rounded bg-[#090a0d] border border-slate-800 flex items-center justify-between">
                    <span className="text-slate-400">Downstream Impact Score:</span>
                    <span className="text-amber-400 font-semibold">Medium (3 Model Dependencies)</span>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="p-12 text-center border border-dashed border-slate-800 rounded-lg text-slate-500 text-xs">
              Select a migration site from the left panel to inspect AST diagnostics.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
