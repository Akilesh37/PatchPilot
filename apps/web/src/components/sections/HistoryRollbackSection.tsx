"use client";

import React, { useState } from "react";
import {
  History,
  RotateCcw,
  GitPullRequest,
  ExternalLink,
  CheckCircle2,
  AlertTriangle,
  Clock,
  ArrowRight,
} from "lucide-react";
import { Migration, AuditEvent } from "../../lib/api";
import { StatusBadge } from "../ui/StatusBadge";
import { EmptyState } from "../ui/EmptyState";

interface HistoryRollbackSectionProps {
  currentMigration: Migration | null;
  migrationHistory: Migration[];
  auditEvents: AuditEvent[];
  githubToken: string;
  setGithubToken: (token: string) => void;
  githubOwner: string;
  setGithubOwner: (owner: string) => void;
  githubRepo: string;
  setGithubRepo: (repo: string) => void;
  githubBaseBranch: string;
  setGithubBaseBranch: (branch: string) => void;
  createdPrUrl: string | null;
  onRollback: () => void;
  onCreatePR: () => void;
  onSelectMigration: (m: Migration) => void;
  loading: boolean;
}

export function HistoryRollbackSection({
  currentMigration,
  migrationHistory,
  auditEvents,
  githubToken,
  setGithubToken,
  githubOwner,
  setGithubOwner,
  githubRepo,
  setGithubRepo,
  githubBaseBranch,
  setGithubBaseBranch,
  createdPrUrl,
  onRollback,
  onCreatePR,
  onSelectMigration,
  loading,
}: HistoryRollbackSectionProps) {
  const [rollbackReason, setRollbackReason] = useState("");
  const [showConfirmRollback, setShowConfirmRollback] = useState(false);

  const allMigrations = migrationHistory.length > 0
    ? migrationHistory
    : currentMigration
    ? [currentMigration]
    : [];

  const isVerifiedPassed = currentMigration?.status === "VERIFIED_PASSED";

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Section Header */}
      <div>
        <h2 className="text-base font-semibold tracking-tight text-slate-100">
          Migration Audit History & Enterprise Rollback
        </h2>
        <p className="text-xs text-slate-400 mt-0.5">
          Review execution audit trails, trigger atomic checkpoint rollback, and export verified changes as GitHub Pull Requests.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column (7 cols): Execution History & Audit Events */}
        <div className="lg:col-span-7 space-y-6">
          {/* Migration Runs Table */}
          <div className="rounded-lg bg-[#11141c] border border-slate-800/80 p-5 space-y-3.5">
            <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
              <div className="flex items-center gap-2">
                <History className="w-4 h-4 text-blue-400" />
                <h3 className="text-sm font-semibold text-slate-100">Execution History</h3>
              </div>
              <span className="text-xs font-mono text-slate-500">
                {allMigrations.length} record(s)
              </span>
            </div>

            {allMigrations.length > 0 ? (
              <div className="border border-slate-800 rounded-md overflow-hidden">
                <table className="w-full text-left text-xs font-mono">
                  <thead className="bg-[#090a0d] border-b border-slate-800 text-[10px] text-slate-400 uppercase tracking-wider">
                    <tr>
                      <th className="py-2.5 px-3">Migration ID</th>
                      <th className="py-2.5 px-3">Framework</th>
                      <th className="py-2.5 px-3">Verification</th>
                      <th className="py-2.5 px-3 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {allMigrations.map((m) => (
                      <tr key={m.id} className="hover:bg-slate-800/30 transition-colors">
                        <td className="py-2.5 px-3 text-slate-300 font-semibold truncate max-w-[140px]">
                          {m.id.slice(0, 8)}...
                        </td>
                        <td className="py-2.5 px-3 text-slate-400">
                          {m.source_version} ➔ {m.target_version}
                        </td>
                        <td className="py-2.5 px-3">
                          <StatusBadge status={m.status} size="sm" />
                        </td>
                        <td className="py-2.5 px-3 text-right">
                          <button
                            onClick={() => onSelectMigration(m)}
                            className="text-blue-400 hover:text-blue-300 text-xs hover:underline cursor-pointer inline-flex items-center gap-1"
                          >
                            <span>Inspect</span>
                            <ArrowRight className="w-3 h-3" />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <EmptyState
                icon={<Clock className="w-5 h-5 text-slate-400" />}
                title="No Migration History"
                description="Completed migration executions and verification checkpoints will appear here."
              />
            )}
          </div>

          {/* Real-time Audit Event Trail */}
          <div className="rounded-lg bg-[#11141c] border border-slate-800/80 p-5 space-y-3.5">
            <h3 className="text-sm font-semibold text-slate-100 flex items-center gap-2">
              <Clock className="w-4 h-4 text-blue-400" />
              <span>Audit Trail & Event Log</span>
            </h3>

            {auditEvents.length > 0 ? (
              <div className="space-y-2 font-mono text-xs max-h-72 overflow-y-auto">
                {auditEvents.map((evt) => (
                  <div
                    key={evt.id}
                    className="p-2.5 rounded bg-[#090a0d] border border-slate-800 flex items-start justify-between gap-3"
                  >
                    <div className="space-y-0.5">
                      <span className="text-blue-400 font-semibold block">{evt.event_type}</span>
                      <span className="text-[11px] text-slate-500 font-sans">
                        Event recorded by verification worker
                      </span>
                    </div>
                    <span className="text-[10px] text-slate-500 shrink-0">
                      {new Date(evt.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="p-6 text-center text-xs text-slate-500 font-mono border border-dashed border-slate-800 rounded">
                No audit events recorded for current session
              </div>
            )}
          </div>
        </div>

        {/* Right Column (5 cols): Atomic Rollback & GitHub PR */}
        <div className="lg:col-span-5 space-y-6">
          {/* 1-Click Atomic Rollback Card */}
          <div className="rounded-lg bg-[#11141c] border border-slate-800/80 p-5 space-y-3.5">
            <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
              <div className="flex items-center gap-2">
                <RotateCcw className="w-4 h-4 text-amber-400" />
                <h3 className="text-sm font-semibold text-slate-100">Transactional Rollback</h3>
              </div>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-amber-950/40 text-amber-300 border border-amber-800/50">
                Atomic
              </span>
            </div>

            <p className="text-xs text-slate-400 leading-relaxed font-sans">
              Instantly restore the target repository to its exact pre-migration state using the transactional snapshot checkpoint.
            </p>

            <div className="space-y-3">
              <input
                type="text"
                placeholder="Reason for rollback (optional)..."
                value={rollbackReason}
                onChange={(e) => setRollbackReason(e.target.value)}
                className="w-full px-3 py-1.5 text-xs rounded-md bg-[#090a0d] border border-slate-800 text-slate-200 placeholder-slate-600 focus:outline-none focus:border-amber-500 font-mono"
              />

              {!showConfirmRollback ? (
                <button
                  onClick={() => setShowConfirmRollback(true)}
                  disabled={loading || !currentMigration}
                  className="w-full flex items-center justify-center gap-1.5 px-3.5 py-2 text-xs font-semibold rounded-md bg-amber-600/10 text-amber-400 hover:bg-amber-600/20 border border-amber-500/30 transition cursor-pointer disabled:opacity-50"
                >
                  <RotateCcw className="w-3.5 h-3.5" />
                  <span>Initiate Checkpoint Rollback</span>
                </button>
              ) : (
                <div className="p-3 rounded-md bg-rose-950/30 border border-rose-800/50 space-y-2">
                  <div className="text-xs text-rose-300 font-medium">
                    Confirm repository rollback? This will discard all synthesized changes.
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => {
                        setShowConfirmRollback(false);
                        onRollback();
                      }}
                      className="flex-1 py-1.5 text-xs font-semibold rounded bg-rose-600 hover:bg-rose-500 text-white cursor-pointer"
                    >
                      Yes, Restore Files
                    </button>
                    <button
                      onClick={() => setShowConfirmRollback(false)}
                      className="px-3 py-1.5 text-xs rounded bg-slate-800 text-slate-300 hover:bg-slate-700 cursor-pointer"
                    >
                      Cancel
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* GitHub PR Integration Card */}
          <div className="rounded-lg bg-[#11141c] border border-slate-800/80 p-5 space-y-3.5">
            <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
              <div className="flex items-center gap-2">
                <GitPullRequest className="w-4 h-4 text-blue-400" />
                <h3 className="text-sm font-semibold text-slate-100">GitHub Pull Request Export</h3>
              </div>
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-blue-950/40 text-blue-300 border border-blue-800/50">
                Policy Gate
              </span>
            </div>

            {/* Policy Check Notice */}
            <div
              className={`p-2.5 rounded-md border text-xs flex items-center gap-2 ${
                isVerifiedPassed
                  ? "bg-emerald-950/20 border-emerald-800/40 text-emerald-300"
                  : "bg-amber-950/20 border-amber-800/40 text-amber-300"
              }`}
            >
              {isVerifiedPassed ? (
                <>
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>Verification passed: Ready to export PR</span>
                </>
              ) : (
                <>
                  <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
                  <span>Verification required before opening PR</span>
                </>
              )}
            </div>

            {/* Inputs */}
            <div className="space-y-3">
              <div>
                <label className="text-xs font-medium text-slate-300 block mb-1">
                  GitHub Personal Access Token (PAT)
                </label>
                <input
                  type="password"
                  placeholder="ghp_************************************"
                  value={githubToken}
                  onChange={(e) => setGithubToken(e.target.value)}
                  className="w-full px-3 py-1.5 text-xs rounded-md bg-[#090a0d] border border-slate-800 text-slate-200 placeholder-slate-600 focus:outline-none focus:border-blue-500 font-mono"
                />
                <span className="text-[10px] text-slate-500 mt-1 block">
                  Tokens are sanitized and never logged or stored.
                </span>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-medium text-slate-300 block mb-1">
                    Owner / Org
                  </label>
                  <input
                    type="text"
                    value={githubOwner}
                    onChange={(e) => setGithubOwner(e.target.value)}
                    className="w-full px-3 py-1.5 text-xs rounded-md bg-[#090a0d] border border-slate-800 text-slate-200 font-mono focus:outline-none focus:border-blue-500"
                  />
                </div>

                <div>
                  <label className="text-xs font-medium text-slate-300 block mb-1">
                    Repository Name
                  </label>
                  <input
                    type="text"
                    value={githubRepo}
                    onChange={(e) => setGithubRepo(e.target.value)}
                    className="w-full px-3 py-1.5 text-xs rounded-md bg-[#090a0d] border border-slate-800 text-slate-200 font-mono focus:outline-none focus:border-blue-500"
                  />
                </div>
              </div>

              <div>
                <label className="text-xs font-medium text-slate-300 block mb-1">
                  Base Branch
                </label>
                <input
                  type="text"
                  value={githubBaseBranch}
                  onChange={(e) => setGithubBaseBranch(e.target.value)}
                  className="w-full px-3 py-1.5 text-xs rounded-md bg-[#090a0d] border border-slate-800 text-slate-200 font-mono focus:outline-none focus:border-blue-500"
                />
              </div>

              <button
                onClick={onCreatePR}
                disabled={loading || !currentMigration}
                className="w-full flex items-center justify-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-md bg-blue-600 hover:bg-blue-500 text-white shadow-sm shadow-blue-600/30 transition cursor-pointer disabled:opacity-50"
              >
                <GitPullRequest className="w-3.5 h-3.5" />
                <span>Create Migration Pull Request</span>
              </button>

              {createdPrUrl && (
                <div className="p-3 rounded-md bg-emerald-950/30 border border-emerald-800/50 flex items-center justify-between text-xs text-emerald-300">
                  <span className="truncate max-w-[200px]">PR: {createdPrUrl}</span>
                  <a
                    href={createdPrUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="text-emerald-400 hover:underline flex items-center gap-1 shrink-0 font-semibold"
                  >
                    <span>View on GitHub</span>
                    <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
