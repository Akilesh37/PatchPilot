"use client";

import React from "react";
import {
  CheckCircle2,
  XCircle,
  Clock,
  RotateCcw,
  ShieldCheck,
  ShieldAlert,
  FileCode2,
  AlertTriangle,
  Loader2,
} from "lucide-react";

interface StatusBadgeProps {
  status?: string;
  className?: string;
  size?: "sm" | "md";
}

export function StatusBadge({ status, className = "", size = "md" }: StatusBadgeProps) {
  const norm = (status || "IDLE").toUpperCase();
  const sizeClasses = size === "sm" ? "px-2 py-0.5 text-[11px]" : "px-2.5 py-1 text-xs";

  switch (norm) {
    case "VERIFIED_PASSED":
    case "PASSED":
      return (
        <span
          className={`inline-flex items-center gap-1.5 font-medium rounded-md bg-emerald-950/40 text-emerald-300 border border-emerald-800/50 ${sizeClasses} ${className}`}
        >
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
          <span>Verified Passed</span>
        </span>
      );

    case "VERIFIED_FAILED":
    case "FAILED":
      return (
        <span
          className={`inline-flex items-center gap-1.5 font-medium rounded-md bg-rose-950/40 text-rose-300 border border-rose-800/50 ${sizeClasses} ${className}`}
        >
          <XCircle className="w-3.5 h-3.5 text-rose-400 shrink-0" />
          <span>Verification Failed</span>
        </span>
      );

    case "APPROVED":
      return (
        <span
          className={`inline-flex items-center gap-1.5 font-medium rounded-md bg-emerald-950/40 text-emerald-300 border border-emerald-800/50 ${sizeClasses} ${className}`}
        >
          <ShieldCheck className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
          <span>Approved</span>
        </span>
      );

    case "REJECTED":
      return (
        <span
          className={`inline-flex items-center gap-1.5 font-medium rounded-md bg-rose-950/40 text-rose-300 border border-rose-800/50 ${sizeClasses} ${className}`}
        >
          <ShieldAlert className="w-3.5 h-3.5 text-rose-400 shrink-0" />
          <span>Rejected</span>
        </span>
      );

    case "ROLLED_BACK":
      return (
        <span
          className={`inline-flex items-center gap-1.5 font-medium rounded-md bg-amber-950/40 text-amber-300 border border-amber-800/50 ${sizeClasses} ${className}`}
        >
          <RotateCcw className="w-3.5 h-3.5 text-amber-400 shrink-0" />
          <span>Rolled Back</span>
        </span>
      );

    case "GENERATED":
    case "PENDING_REVIEW":
      return (
        <span
          className={`inline-flex items-center gap-1.5 font-medium rounded-md bg-sky-950/40 text-sky-300 border border-sky-800/50 ${sizeClasses} ${className}`}
        >
          <FileCode2 className="w-3.5 h-3.5 text-sky-400 shrink-0" />
          <span>Pending Review</span>
        </span>
      );

    case "PLANNING":
    case "EXECUTING":
    case "RUNNING":
      return (
        <span
          className={`inline-flex items-center gap-1.5 font-medium rounded-md bg-blue-950/40 text-blue-300 border border-blue-800/50 ${sizeClasses} ${className}`}
        >
          <Loader2 className="w-3.5 h-3.5 text-blue-400 animate-spin shrink-0" />
          <span>In Progress</span>
        </span>
      );

    default:
      return (
        <span
          className={`inline-flex items-center gap-1.5 font-medium rounded-md bg-slate-800/60 text-slate-300 border border-slate-700/60 ${sizeClasses} ${className}`}
        >
          <Clock className="w-3.5 h-3.5 text-slate-400 shrink-0" />
          <span>{status || "Ready"}</span>
        </span>
      );
  }
}

interface RiskBadgeProps {
  level?: string;
  score?: number;
  className?: string;
}

export function RiskBadge({ level = "LOW", score, className = "" }: RiskBadgeProps) {
  const norm = level.toUpperCase();
  let colorStyles = "bg-slate-800/60 text-slate-300 border-slate-700/60";

  if (norm === "CRITICAL") {
    colorStyles = "bg-rose-950/50 text-rose-300 border-rose-800/60";
  } else if (norm === "HIGH") {
    colorStyles = "bg-orange-950/50 text-orange-300 border-orange-800/60";
  } else if (norm === "MEDIUM") {
    colorStyles = "bg-amber-950/50 text-amber-300 border-amber-800/60";
  } else if (norm === "LOW") {
    colorStyles = "bg-emerald-950/40 text-emerald-300 border-emerald-800/50";
  }

  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 text-[11px] font-mono font-medium rounded border ${colorStyles} ${className}`}
    >
      <AlertTriangle className="w-3 h-3 shrink-0" />
      <span>{norm}</span>
      {score !== undefined && <span className="opacity-70 ml-0.5">({score})</span>}
    </span>
  );
}
