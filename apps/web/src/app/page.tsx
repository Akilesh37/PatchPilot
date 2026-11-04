"use client";

import React, { useState, useEffect } from "react";
import {
  fetchProjects,
  createProject,
  registerRepository,
  analyzeRepository,
  createMigration,
  fetchMigration,
  verifyMigration,
  approvePatch,
  rejectPatch,
  rollbackMigration,
  createGitHubPR,
  fetchMigrationEvents,
  fetchBenchmarkSummary,
  fetchMigrations,
  Project,
  Migration,
  RepoAnalysis,
  BenchmarkReport,
  AuditEvent,
} from "../lib/api";
import { AlertCircle, CheckCircle2, X } from "lucide-react";
import { WorkspaceHeader } from "../components/layout/WorkspaceHeader";
import { SidebarNavigation, NavTab } from "../components/layout/SidebarNavigation";
import { OverviewSection } from "../components/sections/OverviewSection";
import { RepositoryAnalysisSection } from "../components/sections/RepositoryAnalysisSection";
import { MigrationPlannerSection } from "../components/sections/MigrationPlannerSection";
import { CodeReviewSection } from "../components/sections/CodeReviewSection";
import { VerificationSection } from "../components/sections/VerificationSection";
import { HistoryRollbackSection } from "../components/sections/HistoryRollbackSection";

export default function Home() {
  const [activeTab, setActiveTab] = useState<NavTab>("overview");

  const [, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<Project | null>(null);
  const [currentMigration, setCurrentMigration] = useState<Migration | null>(null);
  const [migrationHistory, setMigrationHistory] = useState<Migration[]>([]);
  const [analysis, setAnalysis] = useState<RepoAnalysis | null>(null);
  const [benchmarkReport, setBenchmarkReport] = useState<BenchmarkReport | null>(null);
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([]);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");
  const [successMsg, setSuccessMsg] = useState("");

  // Migration setup
  const [projectName, setProjectName] = useState("Customer Service Migration");
  const [repoPath, setRepoPath] = useState("datasets/fixtures/customer-service-sb2");
  const [sourceVersion, setSourceVersion] = useState("2.7.18");
  const [targetVersion, setTargetVersion] = useState("3.2.0");
  const [patchStrategy, setPatchStrategy] = useState("deterministic");

  // Code Review selection
  const [selectedFileForDiff, setSelectedFileForDiff] = useState<string>("");
  const [reviewerName, setReviewerName] = useState("Lead Platform Engineer");
  const [approvalNotes, setApprovalNotes] = useState("Verified against Jakarta EE 10 baseline.");

  // GitHub PR state
  const [githubToken, setGithubToken] = useState("");
  const [githubOwner, setGithubOwner] = useState("org-example");
  const [githubRepo, setGithubRepo] = useState("customer-service");
  const [githubBaseBranch, setGithubBaseBranch] = useState("main");
  const [createdPrUrl, setCreatedPrUrl] = useState<string | null>(null);

  // Initialize projects & benchmark data
  useEffect(() => {
    let mounted = true;
    async function init() {
      try {
        const projs = await fetchProjects();
        if (!mounted) return;
        setProjects(projs);
        if (projs.length > 0) {
          setSelectedProject(projs[0]);
        }
        const bench = await fetchBenchmarkSummary();
        if (!mounted) return;
        setBenchmarkReport(bench);

        // Fetch recent migrations
        const migs = await fetchMigrations();
        if (!mounted) return;
        setMigrationHistory(migs);
        if (migs.length > 0) {
          setCurrentMigration(migs[0]);
          if (migs[0].patch?.file_diffs) {
            const files = Object.keys(migs[0].patch.file_diffs);
            if (files.length > 0) setSelectedFileForDiff(files[0]);
          }
        }
      } catch (e: unknown) {
        console.warn("Could not connect to live API, demo fallback ready:", e);
      }
    }
    init();
    return () => {
      mounted = false;
    };
  }, []);

  // Run full migration workflow
  async function handleRunMigration() {
    try {
      setLoading(true);
      setErrorMsg("");
      setSuccessMsg("");

      // 1. Create or select project
      let proj = selectedProject;
      if (!proj) {
        proj = await createProject(projectName, "Spring Boot 2 to 3 Migration");
        setProjects((prev) => [proj!, ...prev]);
        setSelectedProject(proj);
      }

      // 2. Ingest repository snapshot
      const snapshot = await registerRepository(proj.id, repoPath);

      // 3. Analyze repository AST
      const repoAnalysis = await analyzeRepository(proj.id);
      setAnalysis(repoAnalysis);

      // 4. Create Migration (Generate Plan + Diff)
      const migration = await createMigration(
        proj.id,
        snapshot.id,
        sourceVersion,
        targetVersion,
        patchStrategy
      );
      setCurrentMigration(migration);
      setMigrationHistory((prev) => [migration, ...prev]);

      if (migration.patch && migration.patch.file_diffs) {
        const files = Object.keys(migration.patch.file_diffs);
        if (files.length > 0) setSelectedFileForDiff(files[0]);
      }

      // 5. Fetch audit events
      const events = await fetchMigrationEvents(migration.id);
      setAuditEvents(events);

      setSuccessMsg("Migration plan and unified diff successfully synthesized.");
      setActiveTab("analysis");
    } catch (e: unknown) {
      setErrorMsg(e instanceof Error ? e.message : "Failed to execute migration workflow");
    } finally {
      setLoading(false);
    }
  }

  // Trigger sandboxed verification
  async function handleVerify() {
    if (!currentMigration) return;
    try {
      setLoading(true);
      setErrorMsg("");
      setSuccessMsg("");

      const run = await verifyMigration(currentMigration.id, 2);
      const updated = await fetchMigration(currentMigration.id);
      setCurrentMigration(updated);

      const events = await fetchMigrationEvents(currentMigration.id);
      setAuditEvents(events);

      if (run.status === "PASSED") {
        setSuccessMsg("Verification PASSED in isolated execution sandbox!");
      } else {
        setErrorMsg("Verification check completed with diagnostics. Inspect repair logs.");
      }
      setActiveTab("verification");
    } catch (e: unknown) {
      setErrorMsg(e instanceof Error ? e.message : "Verification failed");
    } finally {
      setLoading(false);
    }
  }

  // Approve patch
  async function handleApprove() {
    if (!currentMigration) return;
    try {
      setLoading(true);
      await approvePatch(currentMigration.id, reviewerName, approvalNotes);
      const updated = await fetchMigration(currentMigration.id);
      setCurrentMigration(updated);
      setSuccessMsg("Patch approved successfully.");
    } catch (e: unknown) {
      setErrorMsg(e instanceof Error ? e.message : "Failed to approve patch");
    } finally {
      setLoading(false);
    }
  }

  // Reject patch
  async function handleReject() {
    if (!currentMigration) return;
    try {
      setLoading(true);
      await rejectPatch(currentMigration.id, reviewerName, approvalNotes);
      const updated = await fetchMigration(currentMigration.id);
      setCurrentMigration(updated);
      setSuccessMsg("Patch marked as rejected.");
    } catch (e: unknown) {
      setErrorMsg(e instanceof Error ? e.message : "Failed to reject patch");
    } finally {
      setLoading(false);
    }
  }

  // Rollback migration
  async function handleRollback() {
    if (!currentMigration) return;
    try {
      setLoading(true);
      setErrorMsg("");
      const res = await rollbackMigration(currentMigration.id, "User requested rollback from dashboard");
      const updated = await fetchMigration(currentMigration.id);
      setCurrentMigration(updated);
      setSuccessMsg(`Rollback executed: ${res.restored_files.length} file(s) restored.`);
    } catch (e: unknown) {
      setErrorMsg(e instanceof Error ? e.message : "Rollback failed");
    } finally {
      setLoading(false);
    }
  }

  // Create GitHub PR
  async function handleCreatePR() {
    if (!currentMigration) return;
    try {
      setLoading(true);
      setErrorMsg("");
      const res = await createGitHubPR(
        currentMigration.id,
        githubOwner,
        githubRepo,
        githubBaseBranch,
        githubToken
      );
      setCreatedPrUrl(res.pr_url || null);
      setSuccessMsg(`Pull Request created: ${res.pr_url || res.head_branch}`);
    } catch (e: unknown) {
      setErrorMsg(e instanceof Error ? e.message : "Failed to create GitHub Pull Request");
    } finally {
      setLoading(false);
    }
  }

  // Inspect previous migration from history
  function handleSelectMigration(m: Migration) {
    setCurrentMigration(m);
    if (m.patch?.file_diffs) {
      const files = Object.keys(m.patch.file_diffs);
      if (files.length > 0) setSelectedFileForDiff(files[0]);
    }
    setActiveTab("analysis");
  }

  return (
    <div className="min-h-screen bg-[#090a0d] text-slate-100 flex flex-col font-sans selection:bg-blue-600/30 selection:text-blue-200">
      {/* Top Application Header */}
      <WorkspaceHeader
        currentMigration={currentMigration}
        repoPath={repoPath}
        loading={loading}
        onRunMigration={handleRunMigration}
        activeTab={activeTab}
      />

      {/* Toast Notification Banners */}
      {errorMsg && (
        <div className="bg-rose-950/40 border-b border-rose-800/60 px-5 py-2 flex items-center justify-between text-xs text-rose-300">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
            <span>{errorMsg}</span>
          </div>
          <button
            onClick={() => setErrorMsg("")}
            className="text-rose-400 hover:text-rose-200 cursor-pointer"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {successMsg && (
        <div className="bg-emerald-950/40 border-b border-emerald-800/60 px-5 py-2 flex items-center justify-between text-xs text-emerald-300">
          <div className="flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
            <span>{successMsg}</span>
          </div>
          <button
            onClick={() => setSuccessMsg("")}
            className="text-emerald-400 hover:text-emerald-200 cursor-pointer"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      )}

      {/* Main Workstation Body */}
      <div className="flex-1 flex overflow-hidden">
        {/* Navigation Sidebar */}
        <SidebarNavigation
          activeTab={activeTab}
          onTabChange={setActiveTab}
          currentMigration={currentMigration}
          repoPath={repoPath}
        />

        {/* Workspace Content Pane */}
        <main className="flex-1 overflow-y-auto p-6 bg-[#090a0d]">
          {activeTab === "overview" && (
            <OverviewSection
              currentMigration={currentMigration}
              migrationHistory={migrationHistory}
              benchmarkReport={benchmarkReport}
              projectName={projectName}
              setProjectName={setProjectName}
              repoPath={repoPath}
              setRepoPath={setRepoPath}
              sourceVersion={sourceVersion}
              setSourceVersion={setSourceVersion}
              targetVersion={targetVersion}
              setTargetVersion={setTargetVersion}
              patchStrategy={patchStrategy}
              setPatchStrategy={setPatchStrategy}
              loading={loading}
              onRunMigration={handleRunMigration}
              onSelectMigration={handleSelectMigration}
            />
          )}

          {activeTab === "analysis" && (
            <RepositoryAnalysisSection
              analysis={analysis}
              repoPath={repoPath}
              onRunMigration={handleRunMigration}
              loading={loading}
            />
          )}

          {activeTab === "planner" && (
            <MigrationPlannerSection
              currentMigration={currentMigration}
              onRunMigration={handleRunMigration}
              loading={loading}
            />
          )}

          {activeTab === "review" && (
            <CodeReviewSection
              currentMigration={currentMigration}
              selectedFileForDiff={selectedFileForDiff}
              setSelectedFileForDiff={setSelectedFileForDiff}
              reviewerName={reviewerName}
              setReviewerName={setReviewerName}
              approvalNotes={approvalNotes}
              setApprovalNotes={setApprovalNotes}
              onApprove={handleApprove}
              onReject={handleReject}
              loading={loading}
            />
          )}

          {activeTab === "verification" && (
            <VerificationSection
              currentMigration={currentMigration}
              onVerify={handleVerify}
              loading={loading}
            />
          )}

          {activeTab === "history" && (
            <HistoryRollbackSection
              currentMigration={currentMigration}
              migrationHistory={migrationHistory}
              auditEvents={auditEvents}
              githubToken={githubToken}
              setGithubToken={setGithubToken}
              githubOwner={githubOwner}
              setGithubOwner={setGithubOwner}
              githubRepo={githubRepo}
              setGithubRepo={setGithubRepo}
              githubBaseBranch={githubBaseBranch}
              setGithubBaseBranch={setGithubBaseBranch}
              createdPrUrl={createdPrUrl}
              onRollback={handleRollback}
              onCreatePR={handleCreatePR}
              onSelectMigration={handleSelectMigration}
              loading={loading}
            />
          )}
        </main>
      </div>
    </div>
  );
}
