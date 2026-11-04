// TypeScript API client for PatchPilot
export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Project {
  id: string;
  name: string;
  description: string;
  created_at: string;
  updated_at: string;
}

export interface RepositorySnapshot {
  id: string;
  project_id: string;
  repo_path: string;
  archive_hash: string;
  detected_language: string;
  build_system: string;
  spring_boot_version: string;
  java_version: string;
  total_files: number;
  total_migration_sites: number;
  file_manifest: {
    files_count?: number;
    java_files?: number;
    rules_detected?: string[];
    affected_files?: number;
  };
  created_at: string;
}

export interface MigrationSite {
  file_path: string;
  line_number: number;
  rule_id: string;
  confidence: string;
  line_content: string;
  snippet: string;
}

export interface RepoAnalysis {
  project_id: string;
  snapshot_id: string;
  total_files: number;
  java_files_count: number;
  total_migration_sites: number;
  affected_files_count: number;
  rules_detected: string[];
  sites: MigrationSite[];
  unsupported_patterns: string[];
}

export interface EvidenceReference {
  rule_id: string;
  doc_title: string;
  section_title: string;
  canonical_url: string;
  snippet: string;
  target_version: string;
  provenance: string;
  score: number;
}

export interface MigrationPlan {
  id: string;
  migration_id: string;
  goal: string;
  affected_files: string[];
  applicable_rule_ids: string[];
  evidence_references: EvidenceReference[];
  risks: string[];
  validation_steps: string[];
  ambiguities: string[];
  created_at: string;
}

export interface PatchArtifact {
  id: string;
  migration_id: string;
  unified_diff: string;
  changed_files_count: number;
  file_diffs: Record<string, string>;
  applied_rules: string[];
  review_status: string; // PENDING_REVIEW, APPROVED, REJECTED
  approved_by?: string;
  approval_notes?: string;
  reviewed_at?: string;
  created_at: string;
}

export interface VerificationRun {
  id: string;
  migration_id: string;
  attempt_number: number;
  status: string; // PASSED, FAILED, NOT_VERIFIED, TIMEOUT, ERROR
  exit_code: number;
  duration_ms: number;
  logs: string;
  compile_success: boolean;
  test_success: boolean;
  failed_tests: string[];
  repair_triggered: boolean;
  repair_succeeded: boolean;
  diagnostics: {
    findings?: string[];
  };
  created_at: string;
}

export interface Migration {
  id: string;
  project_id: string;
  snapshot_id: string;
  source_version: string;
  target_version: string;
  status: string; // PENDING, PLANNING, GENERATED, VERIFIED_PASSED, VERIFIED_FAILED, APPROVED, REJECTED
  patch_strategy: string;
  created_at: string;
  updated_at: string;
  plan?: MigrationPlan;
  patch?: PatchArtifact;
  verification_runs: VerificationRun[];
}

export interface SystemBenchmarkMetric {
  system_name: string;
  system_code: string;
  total_tasks: number;
  passed_tasks: number;
  build_success_rate: number;
  unit_test_success_rate: number;
  end_to_end_success_rate: number;
  required_change_completion: number;
  unnecessary_edit_rate: number;
  localization_precision: number;
  localization_recall: number;
  localization_f1: number;
  avg_latency_ms: number;
  repair_attempts_avg: number;
  verification_coverage: number;
  execution_tier: string;
}

export interface BenchmarkReport {
  evaluation_timestamp: string;
  dataset_manifest_path: string;
  task_count: number;
  systems: SystemBenchmarkMetric[];
  scaling_ablation_status?: {
    description: string;
    verified_task_count: number;
    is_active_manifest: boolean;
  };
}

export interface AuditEvent {
  id: string;
  event_type: string;
  details: Record<string, unknown>;
  timestamp: string;
}

// API methods
export async function fetchHealth(): Promise<{ status: string }> {
  const res = await fetch(`${API_BASE_URL}/health`);
  return res.json();
}

export async function fetchProjects(): Promise<Project[]> {
  const res = await fetch(`${API_BASE_URL}/api/projects`);
  return res.json();
}

export async function createProject(name: string, description: string): Promise<Project> {
  const res = await fetch(`${API_BASE_URL}/api/projects`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, description }),
  });
  return res.json();
}

export async function registerRepository(projectId: string, localPath: string): Promise<RepositorySnapshot> {
  const res = await fetch(`${API_BASE_URL}/api/projects/${projectId}/repositories`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ local_path: localPath }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to register repository");
  }
  return res.json();
}

export async function analyzeRepository(projectId: string): Promise<RepoAnalysis> {
  const res = await fetch(`${API_BASE_URL}/api/projects/${projectId}/analyze`, {
    method: "POST",
  });
  return res.json();
}

export async function createMigration(
  projectId: string,
  snapshotId: string,
  sourceVersion: string,
  targetVersion: string,
  patchStrategy: string = "deterministic"
): Promise<Migration> {
  const res = await fetch(`${API_BASE_URL}/api/projects/${projectId}/migrations`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      snapshot_id: snapshotId,
      source_version: sourceVersion,
      target_version: targetVersion,
      patch_strategy: patchStrategy,
    }),
  });
  return res.json();
}

export async function fetchMigration(migrationId: string): Promise<Migration> {
  const res = await fetch(`${API_BASE_URL}/api/migrations/${migrationId}`);
  return res.json();
}

export async function fetchMigrations(projectId?: string): Promise<Migration[]> {
  const url = projectId
    ? `${API_BASE_URL}/api/projects/${projectId}/migrations`
    : `${API_BASE_URL}/api/migrations`;
  const res = await fetch(url);
  if (!res.ok) return [];
  return res.json();
}

export async function verifyMigration(migrationId: string, maxRepairAttempts: number = 2): Promise<VerificationRun> {
  const res = await fetch(`${API_BASE_URL}/api/migrations/${migrationId}/verify`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ max_repair_attempts: maxRepairAttempts }),
  });
  return res.json();
}

export async function approvePatch(migrationId: string, reviewerName: string, notes: string): Promise<PatchArtifact> {
  const res = await fetch(`${API_BASE_URL}/api/migrations/${migrationId}/approve`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reviewer_name: reviewerName, notes }),
  });
  return res.json();
}

export async function rejectPatch(migrationId: string, reviewerName: string, notes: string): Promise<PatchArtifact> {
  const res = await fetch(`${API_BASE_URL}/api/migrations/${migrationId}/reject`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reviewer_name: reviewerName, notes }),
  });
  return res.json();
}

export async function fetchMigrationEvents(migrationId: string): Promise<AuditEvent[]> {
  const res = await fetch(`${API_BASE_URL}/api/migrations/${migrationId}/events`);
  return res.json();
}

export async function fetchBenchmarkSummary(): Promise<BenchmarkReport> {
  const res = await fetch(`${API_BASE_URL}/api/benchmark/summary`);
  return res.json();
}

export async function fetchRules(): Promise<Record<string, unknown>[]> {
  const res = await fetch(`${API_BASE_URL}/api/rules`);
  return res.json();
}

export async function rollbackMigration(
  migrationId: string,
  reason: string = ""
): Promise<{ status: string; restored_files: string[]; snapshot_id?: string }> {
  const res = await fetch(`${API_BASE_URL}/api/migrations/${migrationId}/rollback`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reason }),
  });
  return res.json();
}

export async function fetchGitHubRepos(token?: string): Promise<Record<string, unknown>[]> {
  const headers: Record<string, string> = {};
  if (token) headers["X-GitHub-Token"] = token;
  const res = await fetch(`${API_BASE_URL}/api/github/repositories`, { headers });
  if (!res.ok) throw new Error("Failed to load GitHub repositories");
  return res.json();
}

export async function createGitHubPR(
  migrationId: string,
  owner: string,
  repo: string,
  baseBranch: string = "main",
  token?: string
): Promise<{ status: string; pr_url?: string; pr_number?: number; head_branch: string; base_branch: string }> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  if (token) headers["X-GitHub-Token"] = token;
  const res = await fetch(`${API_BASE_URL}/api/migrations/${migrationId}/github-pr`, {
    method: "POST",
    headers,
    body: JSON.stringify({ owner, repo, base_branch: baseBranch }),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to create GitHub Pull Request");
  }
  return res.json();
}
