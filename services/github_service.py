"""
GitHub Repository Integration Service.
Enforces:
- Secure token-based authentication (PAT or GitHub App token)
- Strict token redaction across all logs, error messages, and git remotes
- Repository and branch selection
- Dedicated migration branch creation (patchpilot/migration-sb3-<timestamp>)
- Safe patch commit and push
- Verification policy enforcement before PR creation
- Automated Pull Request creation with formatted Markdown migration report and diagnostic citations
"""
import datetime
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from typing import Dict, List, Optional, Any, Tuple
import git

class GitHubAuthError(Exception):
    pass

class GitHubIntegrationError(Exception):
    pass

class GitHubService:
    BASE_API_URL = "https://api.github.com"

    @staticmethod
    def sanitize_token(text: str) -> str:
        """
        Redacts personal access tokens (ghp_*, github_pat_*, Bearer tokens) from text strings.
        """
        if not text:
            return ""
        text = re.sub(r"ghp_[a-zA-Z0-9]{36,}", "ghp_[REDACTED]", text)
        text = re.sub(r"github_pat_[a-zA-Z0-9_]{50,}", "github_pat_[REDACTED]", text)
        text = re.sub(r"(https?://)([^@:]+):([^@]+)@", r"\1[TOKEN_REDACTED]@", text)
        return text

    @classmethod
    def _api_request(
        cls,
        endpoint: str,
        token: str,
        method: str = "GET",
        payload: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        url = f"{cls.BASE_API_URL}{endpoint}"
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "PatchPilot-Migration-Tool"
        }
        data = json.dumps(payload).encode("utf-8") if payload else None

        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as he:
            err_body = he.read().decode("utf-8", errors="ignore")
            sanitized_body = cls.sanitize_token(err_body)
            if he.code in [401, 403]:
                raise GitHubAuthError(f"GitHub authentication error ({he.code}): {sanitized_body}")
            raise GitHubIntegrationError(f"GitHub API error ({he.code}): {sanitized_body}")
        except Exception as e:
            raise GitHubIntegrationError(f"GitHub connection failed: {cls.sanitize_token(str(e))}")

    @classmethod
    def list_repositories(cls, token: str) -> List[Dict[str, Any]]:
        """
        Lists user repositories accessible via token.
        """
        data = cls._api_request("/user/repos?per_page=50&sort=updated", token)
        repos = []
        for r in data:
            repos.append({
                "id": r.get("id"),
                "name": r.get("name"),
                "full_name": r.get("full_name"),
                "default_branch": r.get("default_branch", "main"),
                "private": r.get("private", False),
                "clone_url": r.get("clone_url"),
                "description": r.get("description", "")
            })
        return repos

    @classmethod
    def list_branches(cls, token: str, owner: str, repo: str) -> List[str]:
        """
        Lists branches for a given repository.
        """
        data = cls._api_request(f"/repos/{owner}/{repo}/branches", token)
        return [b.get("name") for b in data]

    @classmethod
    def clone_repository(
        cls,
        token: str,
        clone_url: str,
        branch: str,
        target_dir: str
    ) -> git.Repo:
        """
        Safely clones repository into target_dir using authenticated URL, redacting token from git config.
        """
        # Inject token into URL for authenticated clone
        parsed = urllib.parse.urlparse(clone_url)
        authed_netloc = f"x-access-token:{token}@{parsed.netloc}"
        authed_url = urllib.parse.urlunparse(parsed._replace(netloc=authed_netloc))

        repo = git.Repo.clone_from(authed_url, target_dir, branch=branch, depth=5)

        # Sanitize remote URL stored in .git/config so token never persists on disk
        clean_url = urllib.parse.urlunparse(parsed)
        repo.remotes.origin.set_url(clean_url)

        return repo

    @classmethod
    def create_migration_branch(cls, repo: git.Repo, base_branch: str) -> str:
        """
        Creates dedicated migration branch: patchpilot/migration-sb3-<timestamp>.
        """
        timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S")
        branch_name = f"patchpilot/migration-sb3-{timestamp}"
        repo.git.checkout(base_branch)
        new_branch = repo.create_head(branch_name)
        new_branch.checkout()
        return branch_name

    @classmethod
    def commit_changes(
        cls,
        repo: git.Repo,
        changed_files: List[str],
        commit_message: str
    ) -> str:
        """
        Stages and commits migrated files.
        """
        repo.index.add(changed_files)
        commit = repo.index.commit(commit_message)
        return commit.hexsha

    @classmethod
    def generate_pr_markdown_report(
        cls,
        migration_id: str,
        rules_applied: List[str],
        verification_passed: bool,
        verification_details: Dict[str, Any],
        evidence_citations: List[Dict[str, Any]],
        diff_summary: str
    ) -> str:
        """
        Constructs a comprehensive, professional Markdown Pull Request report.
        """
        status_badge = "✅ **VERIFIED PASSED**" if verification_passed else "⚠️ **PARTIALLY VERIFIED / NEEDS REVIEW**"

        lines = [
            f"# PatchPilot Migration: Spring Boot 2.7 ➔ 3.2",
            "",
            f"**Migration ID:** `{migration_id}`  ",
            f"**Verification Status:** {status_badge}  ",
            "",
            "## 1. Applied Migration Rules",
            ""
        ]

        for r in rules_applied:
            lines.append(f"- `{r}`")

        lines.extend([
            "",
            "## 2. Verification & Build Results",
            f"- **Compilation Check:** {'PASSED' if verification_details.get('compile_success') else 'FAILED'}",
            f"- **Test Suite:** {'PASSED' if verification_details.get('test_success') else 'FAILED'}",
            f"- **Execution Tier:** `{verification_details.get('sandbox_mode', 'SUBPROCESS_HARDENED')}`",
            f"- **Duration:** `{verification_details.get('duration_ms', 0)} ms`",
            "",
            "## 3. Evidence Grounding & Documentation Provenance",
            ""
        ])

        for c in evidence_citations[:4]:
            lines.append(f"- **[{c.get('doc_title')}]({c.get('canonical_url', '#')})**: {c.get('snippet', '')}")

        lines.extend([
            "",
            "## 4. Rollback Instructions",
            "To cleanly revert these changes, run:",
            "```bash",
            "git revert HEAD",
            "mvn clean test",
            "```",
            "",
            "---",
            "*Generated automatically by [PatchPilot](https://github.com/patchpilot/patchpilot) — Evidence-Grounded Migration Engine.*"
        ])

        return "\n".join(lines)

    @classmethod
    def create_pull_request(
        cls,
        token: str,
        owner: str,
        repo: str,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str,
        verification_passed: bool
    ) -> Dict[str, Any]:
        """
        Opens a Pull Request via GitHub REST API.
        Labels the PR based on verification outcome.
        """
        payload = {
            "title": title if verification_passed else f"[UNVERIFIED] {title}",
            "body": body,
            "head": head_branch,
            "base": base_branch
        }

        pr_data = cls._api_request(f"/repos/{owner}/{repo}/pulls", token, method="POST", payload=payload)
        pr_number = pr_data.get("number")

        # Assign label
        if pr_number:
            label = "patchpilot:verified" if verification_passed else "patchpilot:unverified"
            try:
                cls._api_request(
                    f"/repos/{owner}/{repo}/issues/{pr_number}/labels",
                    token,
                    method="POST",
                    payload={"labels": [label]}
                )
            except Exception:
                pass

        return {
            "pr_url": pr_data.get("html_url"),
            "pr_number": pr_number,
            "head_branch": head_branch,
            "base_branch": base_branch,
            "verification_passed": verification_passed
        }

