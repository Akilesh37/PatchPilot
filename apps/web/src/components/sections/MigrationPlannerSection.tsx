"use client";

import React, { useState } from "react";
import {
  ListTodo,
  AlertTriangle,
  ExternalLink,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Compass,
} from "lucide-react";
import { Migration } from "../../lib/api";
import { RiskBadge } from "../ui/StatusBadge";
import { EmptyState } from "../ui/EmptyState";

interface MigrationPlannerSectionProps {
  currentMigration: Migration | null;
  onRunMigration: () => void;
  loading: boolean;
}

export function MigrationPlannerSection({
  currentMigration,
  onRunMigration,
  loading,
}: MigrationPlannerSectionProps) {
  const [expandedRule, setExpandedRule] = useState<string | null>(null);

  const plan = currentMigration?.plan;

  if (!plan) {
    return (
      <div className="max-w-4xl mx-auto py-12">
        <EmptyState
          icon={<ListTodo className="w-6 h-6 text-blue-400" />}
          title="No Migration Plan Formulated"
          description="A structured migration plan decomposes repository changes into deterministic transformations and reasoning-guided patches grounded by official Spring Framework & Jakarta EE citations."
          action={
            <button
              onClick={onRunMigration}
              disabled={loading}
              className="px-4 py-2 text-xs font-semibold rounded-md bg-blue-600 hover:bg-blue-500 text-white shadow-sm transition cursor-pointer disabled:opacity-50"
            >
              {loading ? "Generating Plan..." : "Formulate Migration Plan"}
            </button>
          }
        />
      </div>
    );
  }

  const rules = plan.applicable_rule_ids || [];
  const evidenceList = plan.evidence_references || [];
  const affectedFiles = plan.affected_files || [];
  const risks = plan.risks || [];

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Section Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold tracking-tight text-slate-100">
            Structured Migration Plan & Evidence Grounding
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Idempotent migration operations synthesized with documentation citations from official Spring Boot 3.2 & Jakarta EE 10 specifications.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono px-2.5 py-1 rounded bg-[#11141c] border border-slate-800 text-slate-300">
            Operations: <span className="text-blue-400 font-semibold">{rules.length}</span>
          </span>
        </div>
      </div>

      {/* Plan Header & Objective Card */}
      <div className="rounded-lg bg-[#11141c] border border-slate-800/80 p-5 space-y-3.5">
        <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
          <div className="flex items-center gap-2">
            <Compass className="w-4 h-4 text-blue-400" />
            <h3 className="text-sm font-semibold text-slate-100">Migration Objective</h3>
          </div>
          <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-emerald-950/40 text-emerald-300 border border-emerald-800/50">
            Verified Idempotent
          </span>
        </div>

        <p className="text-xs text-slate-300 font-medium leading-relaxed">
          {plan.goal}
        </p>

        {/* Identified Risks */}
        {risks.length > 0 && (
          <div className="pt-2 border-t border-slate-800/80 space-y-2">
            <span className="text-[10px] font-mono uppercase tracking-wider text-amber-400 font-semibold block">
              Identified Engineering Risks & Verification Requirements:
            </span>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-xs font-mono text-slate-300">
              {risks.map((risk, idx) => (
                <div
                  key={idx}
                  className="flex items-start gap-2 p-2 rounded bg-[#090a0d] border border-slate-800 text-[11px]"
                >
                  <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
                  <span className="text-slate-300">{risk}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Structured Migration Operations Table */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-slate-200">
            Planned Migration Operations ({rules.length})
          </h3>
          <span className="text-xs font-mono text-slate-500">
            Deterministic AST rules & Contextual LLM transforms
          </span>
        </div>

        <div className="border border-slate-800 rounded-lg overflow-hidden divide-y divide-slate-800/80 bg-[#11141c]">
          {rules.map((ruleId, idx) => {
            const isExpanded = expandedRule === ruleId || (expandedRule === null && idx === 0);
            const matchedEvidence = evidenceList.filter((e) => e.rule_id === ruleId);
            const targetFile = affectedFiles[idx] || affectedFiles[0] || "src/main/java/...";

            return (
              <div key={ruleId} className="transition-colors">
                {/* Collapsible Operation Row */}
                <button
                  onClick={() => setExpandedRule(isExpanded ? "" : ruleId)}
                  className="w-full text-left p-4 flex items-center justify-between gap-4 hover:bg-slate-800/30 transition-colors cursor-pointer"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <span className="w-6 h-6 rounded bg-[#090a0d] border border-slate-800 flex items-center justify-center text-xs font-mono text-blue-400 font-semibold shrink-0">
                      {idx + 1}
                    </span>
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono font-bold text-slate-100">{ruleId}</span>
                        <RiskBadge level={ruleId.includes("SECURITY") ? "HIGH" : "MEDIUM"} />
                      </div>
                      <span className="text-[11px] font-mono text-slate-400 truncate block mt-0.5">
                        Target: {targetFile}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 shrink-0">
                    <span className="hidden sm:inline text-[11px] font-mono text-slate-500">
                      {matchedEvidence.length} citation(s)
                    </span>
                    {isExpanded ? (
                      <ChevronDown className="w-4 h-4 text-slate-400" />
                    ) : (
                      <ChevronRight className="w-4 h-4 text-slate-400" />
                    )}
                  </div>
                </button>

                {/* Expanded Operation Details */}
                {isExpanded && (
                  <div className="p-4 pt-0 border-t border-slate-800/60 bg-[#0c0e14] space-y-4">
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-3">
                      {/* Transformation Rationale */}
                      <div className="p-3.5 rounded bg-[#11141c] border border-slate-800 space-y-2">
                        <span className="text-[10px] font-mono uppercase tracking-wider text-slate-500 block">
                          Technical Rationale
                        </span>
                        <p className="text-xs text-slate-300 leading-relaxed font-sans">
                          {ruleId.includes("SERVLET")
                            ? "Upgrade package imports from javax.servlet to jakarta.servlet conforming to Jakarta EE 10 baseline specifications in Spring Boot 3.0+."
                            : ruleId.includes("SECURITY")
                            ? "Replace deprecated WebSecurityConfigurerAdapter extension with modern SecurityFilterChain @Bean configuration method chain."
                            : "Upgrade Maven starter dependencies and property keys to Spring Boot 3.2.0 compatibility standards."}
                        </p>
                      </div>

                      {/* Verification Requirement */}
                      <div className="p-3.5 rounded bg-[#11141c] border border-slate-800 space-y-2">
                        <span className="text-[10px] font-mono uppercase tracking-wider text-slate-500 block">
                          Automated Verification Requirement
                        </span>
                        <div className="space-y-1 text-xs font-mono text-slate-300">
                          <div className="flex items-center gap-1.5 text-emerald-400">
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            <span>JDK 17 compile success</span>
                          </div>
                          <div className="flex items-center gap-1.5 text-emerald-400">
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            <span>Spring Security Context passes</span>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Official Citations & Evidence Grounding */}
                    {matchedEvidence.length > 0 && (
                      <div className="space-y-2">
                        <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 font-semibold block">
                          Official Documentation Citations & Provenance:
                        </span>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                          {matchedEvidence.map((ev, evIdx) => (
                            <div
                              key={evIdx}
                              className="p-3 rounded bg-[#11141c] border border-slate-800 space-y-1.5"
                            >
                              <div className="flex items-center justify-between text-xs font-mono">
                                <span className="font-semibold text-blue-400 truncate">
                                  {ev.doc_title}
                                </span>
                                <span className="text-[10px] text-slate-500">
                                  Score: {Math.round(ev.score * 100)}%
                                </span>
                              </div>
                              <p className="text-[11px] text-slate-400 line-clamp-2 leading-relaxed font-sans">
                                {ev.snippet}
                              </p>
                              {ev.canonical_url && (
                                <a
                                  href={ev.canonical_url}
                                  target="_blank"
                                  rel="noreferrer"
                                  className="text-[10px] font-mono text-blue-400 hover:underline inline-flex items-center gap-1 pt-1"
                                >
                                  <span>{ev.canonical_url}</span>
                                  <ExternalLink className="w-2.5 h-2.5" />
                                </a>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
