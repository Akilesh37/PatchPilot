"use client";

import React from "react";

interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description: string;
  action?: React.ReactNode;
  className?: string;
}

export function EmptyState({
  icon,
  title,
  description,
  action,
  className = "",
}: EmptyStateProps) {
  return (
    <div
      className={`flex flex-col items-center justify-center p-12 text-center rounded-lg border border-dashed border-slate-800 bg-slate-900/20 ${className}`}
    >
      {icon && (
        <div className="w-10 h-10 rounded-lg bg-slate-800/80 border border-slate-700/60 flex items-center justify-center text-slate-400 mb-3 shadow-inner">
          {icon}
        </div>
      )}
      <h3 className="text-sm font-semibold text-slate-200 tracking-tight">{title}</h3>
      <p className="mt-1 text-xs text-slate-400 max-w-md leading-relaxed">{description}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

