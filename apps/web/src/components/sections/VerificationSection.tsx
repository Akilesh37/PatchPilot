"use client";

import React, { useState } from "react";
import {
  Terminal,
  ShieldCheck,
  CheckCircle2,
  XCircle,
  RotateCw,
  Cpu,
  Clock,
  Copy,
  Check,
  AlertTriangle,
  Play,
} from "lucide-react";
import { Migration, VerificationRun } from "../../lib/api";
import { StatusBadge } from "../ui/StatusBadge";
import { EmptyState } from "../ui/EmptyState";

interface VerificationSectionProps {
  currentMigration: Migration | null;
  onVerify: () => void;
  loading: boolean;
}

export function VerificationSection({
  currentMigration,
  onVerify,
  loading,
}: VerificationSectionProps) {
  const [copiedLogs, setCopiedLogs] = useState(false);

  const verificationRuns = currentMigration?.verification_runs || [];
  const activeRun: VerificationRun | undefined = verificationRuns[0];

  const handleCopyLogs = () => {
    if (!activeRun?.logs) return;
    navigator.clipboard.writeText(activeRun.logs);
    setCopiedLogs(true);
    setTimeout(() => setCopiedLogs(false), 2000);
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Section Header & Execution Trigger */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-5 rounded-lg bg-[#11141c] border border-slate-800/80">
        <div>
          <div className="flex items-center gap-2.5">
            <h2 className="text-base font-semibold tracking-tight text-slate-100">
              Isolated Execution Sandbox & Verification
            </h2>
            {activeRun && <StatusBadge status={activeRun.status} size="sm" />}
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Execute rootless container or hardened subprocess compilation and JUnit testing with autonomous diagnostic repair.
          </p>
        </div>

        <button
          onClick={onVerify}
          disabled={loading || !currentMigration}
          className="flex items-center justify-center gap-2 px-4 py-2 text-xs font-semibold rounded-md bg-blue-600 hover:bg-blue-500 text-white shadow-sm shadow-blue-600/30 transition cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed shrink-0"
        >
          {loading ? (
            <RotateCw className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <Play className="w-3.5 h-3.5 fill-current" />
          )}
          <span>{loading ? "Verifying in Sandbox..." : "Execute Verification Check"}</span>
        </button>
      </div>

      {activeRun ? (
        <div className="space-y-6">
          {/* Sandbox Metrics & Environment Parameters */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3.5">
            <div className="p-3.5 rounded-lg bg-[#11141c] border border-slate-800/80">
              <span className="text-[10px] font-mono uppercase tracking-wider text-slate-500 block">
                Sandbox Execution Tier
              </span>
              <div className="flex items-center gap-1.5 mt-1">
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
                <span className="text-sm font-semibold font-mono text-slate-200">
                  Tier 2 Hardened
                </span>
              </div>
              <span className="text-[11px] text-slate-500 mt-0.5 block truncate">
                Subprocess Process Group
              </span>
            </div>

            <div className="p-3.5 rounded-lg bg-[#11141c] border border-slate-800/80">
              <span className="text-[10px] font-mono uppercase tracking-wider text-slate-500 block">
                Exit Code
              </span>
              <div className="flex items-center gap-1.5 mt-1 font-mono">
                {activeRun.exit_code === 0 ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                ) : (
                  <XCircle className="w-4 h-4 text-rose-400" />
                )}
                <span
                  className={`text-sm font-semibold ${
                    activeRun.exit_code === 0 ? "text-emerald-400" : "text-rose-400"
                  }`}
                >
                  Exit {activeRun.exit_code}
                </span>
              </div>
              <span className="text-[11px] text-slate-500 mt-0.5 block truncate">
                {activeRun.exit_code === 0 ? "Successful execution" : "Non-zero exit"}
              </span>
            </div>

            <div className="p-3.5 rounded-lg bg-[#11141c] border border-slate-800/80">
              <span className="text-[10px] font-mono uppercase tracking-wider text-slate-500 block">
                Execution Duration
              </span>
              <div className="flex items-center gap-1.5 mt-1 font-mono">
                <Clock className="w-4 h-4 text-blue-400" />
                <span className="text-sm font-semibold text-slate-200">
                  {activeRun.duration_ms} ms
                </span>
              </div>
              <span className="text-[11px] text-slate-500 mt-0.5 block truncate">
                Build & test execution
              </span>
            </div>

            <div className="p-3.5 rounded-lg bg-[#11141c] border border-slate-800/80">
              <span className="text-[10px] font-mono uppercase tracking-wider text-slate-500 block">
                Resource Capping
              </span>
              <div className="flex items-center gap-1.5 mt-1 font-mono">
                <Cpu className="w-4 h-4 text-slate-400" />
                <span className="text-sm font-semibold text-slate-200">2048 MB / 2 Core</span>
              </div>
              <span className="text-[11px] text-slate-500 mt-0.5 block truncate">
                Network: Isolated (--network none)
              </span>
            </div>
          </div>

          {/* Diagnostic Repair Loop & Findings (if triggered or failed) */}
          {(activeRun.repair_triggered || !activeRun.compile_success || !activeRun.test_success) && (
            <div className="rounded-lg bg-[#11141c] border border-slate-800/80 p-5 space-y-3">
              <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-amber-400" />
                  <h3 className="text-sm font-semibold text-slate-100">
                    Autonomous Diagnostic Repair Loop
                  </h3>
                </div>
                <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-amber-950/40 text-amber-300 border border-amber-800/50">
                  Iteration {activeRun.attempt_number}
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs font-mono">
                <div className="p-3 rounded bg-[#090a0d] border border-slate-800 space-y-1">
                  <span className="text-[10px] text-slate-500 uppercase tracking-wider block">
                    Failure Classification
                  </span>
                  <span className="text-rose-400 font-semibold">
                    {!activeRun.compile_success
                      ? "COMPILATION_ERROR"
                      : !activeRun.test_success
                      ? "TEST_FAILURE"
                      : "CLEAN"}
                  </span>
                </div>

                <div className="p-3 rounded bg-[#090a0d] border border-slate-800 space-y-1">
                  <span className="text-[10px] text-slate-500 uppercase tracking-wider block">
                    Repair Patch Synthesis
                  </span>
                  <span className="text-emerald-400 font-semibold">
                    {activeRun.repair_succeeded ? "Auto-Repaired via RAG" : "Not Required"}
                  </span>
                </div>

                <div className="p-3 rounded bg-[#090a0d] border border-slate-800 space-y-1">
                  <span className="text-[10px] text-slate-500 uppercase tracking-wider block">
                    Remaining Attempts
                  </span>
                  <span className="text-slate-300 font-semibold">
                    {Math.max(0, 2 - activeRun.attempt_number)} attempt(s)
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Terminal-Style Log Console Viewer */}
          <div className="rounded-lg bg-[#0e1117] border border-slate-800/80 overflow-hidden shadow-xl">
            {/* Terminal Header Bar */}
            <div className="px-4 py-2.5 bg-[#090a0d] border-b border-slate-800 flex items-center justify-between select-none">
              <div className="flex items-center gap-2">
                <div className="flex items-center gap-1.5">
                  <span className="w-2.5 h-2.5 rounded-full bg-rose-500/80" />
                  <span className="w-2.5 h-2.5 rounded-full bg-amber-500/80" />
                  <span className="w-2.5 h-2.5 rounded-full bg-emerald-500/80" />
                </div>
                <span className="text-xs font-mono text-slate-400 ml-2">
                  verification_sandbox_execution.log
                </span>
              </div>

              <button
                onClick={handleCopyLogs}
                className="flex items-center gap-1 px-2 py-1 text-xs font-mono text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 rounded transition cursor-pointer"
              >
                {copiedLogs ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copiedLogs ? "Copied" : "Copy Logs"}</span>
              </button>
            </div>

            {/* Terminal Output */}
            <div className="p-4 bg-[#08090d] font-mono text-xs max-h-[550px] overflow-y-auto leading-relaxed select-text">
              {activeRun.logs ? (
                <div className="space-y-0.5">
                  {activeRun.logs.split("\n").map((line, idx) => {
                    let lineStyle = "text-slate-300";

                    if (line.includes("[ERROR]") || line.includes("BUILD FAILURE") || line.includes("FAILURES!")) {
                      lineStyle = "text-rose-400 font-semibold bg-rose-950/20";
                    } else if (line.includes("[WARNING]")) {
                      lineStyle = "text-amber-400";
                    } else if (line.includes("BUILD SUCCESS") || line.includes("OK (") || line.includes("Passed")) {
                      lineStyle = "text-emerald-400 font-semibold";
                    } else if (line.startsWith("[INFO]") || line.startsWith("---")) {
                      lineStyle = "text-slate-500";
                    }

                    return (
                      <div key={idx} className={`flex items-start gap-3 px-1.5 rounded-sm ${lineStyle}`}>
                        <span className="text-slate-600 select-none text-right w-8 shrink-0 text-[11px]">
                          {idx + 1}
                        </span>
                        <pre className="flex-1 overflow-x-visible whitespace-pre-wrap">{line}</pre>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="text-slate-500 text-center py-8">
                  Execution completed without diagnostic log stream.
                </div>
              )}
            </div>
          </div>
        </div>
      ) : (
        <EmptyState
          icon={<Terminal className="w-6 h-6 text-blue-400" />}
          title="No Verification Executed"
          description="Click 'Execute Verification Check' above to run the isolated build and test verification pipeline in the hardened execution sandbox."
          action={
            <button
              onClick={onVerify}
              disabled={loading || !currentMigration}
              className="px-4 py-2 text-xs font-semibold rounded-md bg-blue-600 hover:bg-blue-500 text-white shadow-sm transition cursor-pointer disabled:opacity-50"
            >
              {loading ? "Verifying..." : "Run Sandbox Verification"}
            </button>
          }
        />
      )}
    </div>
  );
}
