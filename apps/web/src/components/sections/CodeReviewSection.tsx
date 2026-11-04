"use client";

import React from "react";
import {
  FileDiff,
  Check,
  X,
  FileCode2,
} from "lucide-react";
import { Migration, PatchArtifact } from "../../lib/api";
import { StatusBadge } from "../ui/StatusBadge";
import { EmptyState } from "../ui/EmptyState";

interface CodeReviewSectionProps {
  currentMigration: Migration | null;
  selectedFileForDiff: string;
  setSelectedFileForDiff: (file: string) => void;
  reviewerName: string;
  setReviewerName: (name: string) => void;
  approvalNotes: string;
  setApprovalNotes: (notes: string) => void;
  onApprove: () => void;
  onReject: () => void;
  loading: boolean;
}

export function CodeReviewSection({
  currentMigration,
  selectedFileForDiff,
  setSelectedFileForDiff,
  reviewerName,
  setReviewerName,
  approvalNotes,
  setApprovalNotes,
  onApprove,
  onReject,
  loading,
}: CodeReviewSectionProps) {
  const patch: PatchArtifact | undefined = currentMigration?.patch;

  if (!patch) {
    return (
      <div className="max-w-4xl mx-auto py-12">
        <EmptyState
          icon={<FileDiff className="w-6 h-6 text-blue-400" />}
          title="No Patch Available for Review"
          description="Synthesize an idempotent migration patch through the Overview tab to inspect unified before-and-after diffs, approve changes, or reject unverified modifications."
        />
      </div>
    );
  }

  const fileDiffs = patch.file_diffs || {};
  const fileKeys = Object.keys(fileDiffs);
  const activeFile = selectedFileForDiff || fileKeys[0] || "";
  const rawDiff = fileDiffs[activeFile] || patch.unified_diff || "";

  // Parse raw diff into formatted lines
  const diffLines = rawDiff.split("\n");

  const isApproved = patch.review_status === "APPROVED";
  const isRejected = patch.review_status === "REJECTED";

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Top Review Bar */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 p-4 rounded-lg bg-[#11141c] border border-slate-800/80">
        <div>
          <div className="flex items-center gap-2.5">
            <h2 className="text-base font-semibold tracking-tight text-slate-100">
              Code Review & Unified Diffs
            </h2>
            <StatusBadge status={patch.review_status} size="sm" />
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Inspect line-by-line transformations before changes are committed or pull requests created.
          </p>
        </div>

        {/* Approval / Rejection Controls */}
        <div className="flex flex-wrap items-center gap-2.5">
          <input
            type="text"
            placeholder="Reviewer Name"
            value={reviewerName}
            onChange={(e) => setReviewerName(e.target.value)}
            disabled={isApproved || loading}
            className="px-2.5 py-1.5 text-xs rounded-md bg-[#090a0d] border border-slate-800 text-slate-200 placeholder-slate-600 focus:outline-none focus:border-blue-500 font-mono w-36 transition"
          />

          <input
            type="text"
            placeholder="Approval / Review notes..."
            value={approvalNotes}
            onChange={(e) => setApprovalNotes(e.target.value)}
            disabled={isApproved || loading}
            className="px-2.5 py-1.5 text-xs rounded-md bg-[#090a0d] border border-slate-800 text-slate-200 placeholder-slate-600 focus:outline-none focus:border-blue-500 font-mono w-52 transition"
          />

          <button
            onClick={onApprove}
            disabled={loading || isApproved}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-md bg-emerald-600 hover:bg-emerald-500 text-white shadow-sm shadow-emerald-600/20 transition cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Check className="w-3.5 h-3.5" />
            <span>{isApproved ? "Approved" : "Approve Patch"}</span>
          </button>

          <button
            onClick={onReject}
            disabled={loading || isRejected}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-md bg-rose-600 hover:bg-rose-500 text-white shadow-sm shadow-rose-600/20 transition cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <X className="w-3.5 h-3.5" />
            <span>{isRejected ? "Rejected" : "Reject"}</span>
          </button>
        </div>
      </div>

      {/* Main Review Layout: File Tree (Left) + Diff Viewer (Right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left Column (4 cols): Changed Files List */}
        <div className="lg:col-span-4 rounded-lg bg-[#11141c] border border-slate-800/80 overflow-hidden">
          <div className="p-3 border-b border-slate-800/80 bg-[#0c0e14] flex items-center justify-between">
            <span className="text-xs font-mono uppercase tracking-wider text-slate-400 font-semibold">
              Changed Files ({fileKeys.length})
            </span>
            <span className="text-[10px] font-mono text-slate-500">Unified Format</span>
          </div>

          <div className="divide-y divide-slate-800/60 font-mono text-xs max-h-[600px] overflow-y-auto">
            {fileKeys.map((file) => {
              const isSelected = activeFile === file;
              const shortName = file.split("/").pop() || file;
              const dirPath = file.split("/").slice(0, -1).join("/");

              return (
                <button
                  key={file}
                  onClick={() => setSelectedFileForDiff(file)}
                  className={`w-full text-left p-3 transition-colors cursor-pointer flex items-start justify-between gap-2 ${
                    isSelected
                      ? "bg-blue-600/10 border-l-2 border-blue-500 text-slate-100"
                      : "hover:bg-slate-800/30 text-slate-400"
                  }`}
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-200">
                      <FileCode2 className="w-3.5 h-3.5 text-blue-400 shrink-0" />
                      <span className="truncate">{shortName}</span>
                    </div>
                    {dirPath && (
                      <span className="text-[10px] text-slate-500 truncate block mt-0.5">
                        {dirPath}
                      </span>
                    )}
                  </div>

                  <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-400">
                    diff
                  </span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Right Column (8 cols): GitHub / IDE Style Diff Viewer */}
        <div className="lg:col-span-8 rounded-lg bg-[#11141c] border border-slate-800/80 overflow-hidden">
          {/* File Header */}
          <div className="p-3.5 border-b border-slate-800/80 bg-[#0c0e14] flex items-center justify-between">
            <div className="flex items-center gap-2 min-w-0">
              <span className="text-xs font-mono font-semibold text-slate-200 truncate">
                {activeFile || "unified.diff"}
              </span>
            </div>

            <div className="flex items-center gap-2 text-xs font-mono text-slate-400">
              <span className="text-emerald-400">+ additions</span>
              <span>&middot;</span>
              <span className="text-rose-400">- deletions</span>
            </div>
          </div>

          {/* Line-by-Line Colorized Diff Content */}
          <div className="bg-[#090a0d] p-3 font-mono text-xs overflow-x-auto max-h-[620px] select-text">
            {diffLines.length > 0 ? (
              <div className="space-y-0.5 leading-relaxed">
                {diffLines.map((line, idx) => {
                  let lineClass = "text-slate-300";
                  let rowBackground = "";

                  if (line.startsWith("@@")) {
                    lineClass = "text-blue-400 font-semibold";
                    rowBackground = "bg-blue-950/20 text-blue-300 py-1";
                  } else if (line.startsWith("+") && !line.startsWith("+++")) {
                    lineClass = "text-emerald-300";
                    rowBackground = "bg-emerald-950/25";
                  } else if (line.startsWith("-") && !line.startsWith("---")) {
                    lineClass = "text-rose-300";
                    rowBackground = "bg-rose-950/25";
                  } else if (line.startsWith("diff ") || line.startsWith("index ")) {
                    lineClass = "text-slate-500 font-semibold";
                  }

                  return (
                    <div
                      key={idx}
                      className={`flex items-start gap-3 px-2 rounded-sm ${rowBackground}`}
                    >
                      <span className="text-slate-600 select-none text-right w-8 shrink-0 text-[11px]">
                        {idx + 1}
                      </span>
                      <pre className={`flex-1 overflow-x-visible whitespace-pre ${lineClass}`}>
                        {line}
                      </pre>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="p-8 text-center text-xs text-slate-500 font-mono">
                No diff lines available for selected file.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
