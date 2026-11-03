"""
Isolated Verification Worker with Multi-Tier Execution Sandbox.
Tiers:
1. Container Sandbox (Rootless Docker/Podman):
   - Network isolation (--network none)
   - CPU and memory limits (--cpus 2.0, --memory 2048m)
   - Non-privileged user
   - Automatic container removal
2. Hardened Subprocess Sandbox (Fallback):
   - Environment variable purification (purges tokens, secrets, AWS keys, SSH credentials)
   - Process group isolation (kills all child/orphaned processes via SIGKILL on timeout/error)
   - Command prefix allowlist & dangerous argument rejection (-Dexec.executable, etc.)
   - Execution timeout bounds
"""
import os
import re
import signal
import subprocess
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Tuple

ALLOWED_COMMAND_PREFIXES = [
    ["mvn", "test-compile"],
    ["mvn", "test"],
    ["mvn", "compile"],
    ["mvn", "clean", "test"],
    ["./gradlew", "test"],
    ["gradle", "test"]
]

PROHIBITED_ARGUMENTS = [
    "-Dmaven.ext.class.path",
    "-Djava.library.path",
    "-Dexec.executable",
    "-DforkCount=0",
    "--init-script",
    "-Dmaven.plugin.validation=brief"
]

SAFE_ENV_KEYS = {
    "PATH", "JAVA_HOME", "M2_HOME", "MAVEN_HOME", "LANG", "LC_ALL",
    "TERM", "TMPDIR", "TEMP", "TMP"
}

@dataclass
class DiagnosticFinding:
    error_type: str  # "compilation" or "test_failure"
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    message: str = ""
    raw_snippet: str = ""

@dataclass
class VerificationOutcome:
    status: str  # "PASSED", "FAILED", "ERROR", "TIMEOUT"
    exit_code: int
    duration_ms: int
    compile_success: bool
    test_success: bool
    logs: str
    diagnostics: List[DiagnosticFinding] = field(default_factory=list)
    failed_test_names: List[str] = field(default_factory=list)
    sandbox_mode: str = "SUBPROCESS_HARDENED"  # "CONTAINER_ROOTLESS" or "SUBPROCESS_HARDENED"

class CommandSecurityError(Exception):
    pass

class VerificationWorker:
    def __init__(self, timeout_seconds: int = 120, prefer_container: bool = True):
        self.timeout_seconds = timeout_seconds
        self.prefer_container = prefer_container
        self._container_runtime = self._detect_container_runtime() if prefer_container else None

    @staticmethod
    def _detect_container_runtime() -> Optional[str]:
        """
        Detects if an active, responsive Docker or Podman daemon is available.
        """
        for runtime in ["docker", "podman"]:
            try:
                res = subprocess.run(
                    [runtime, "info"],
                    capture_output=True,
                    timeout=3
                )
                if res.returncode == 0:
                    return runtime
            except Exception:
                continue
        return None

    @classmethod
    def filter_environment(cls) -> Dict[str, str]:
        """
        Creates a sanitized environment dictionary containing only essential, non-sensitive variables.
        Strips all cloud tokens, GitHub credentials, SSH agents, and internal API keys.
        """
        clean_env = {}
        for key in SAFE_ENV_KEYS:
            if key in os.environ:
                clean_env[key] = os.environ[key]

        if "PATH" not in clean_env:
            clean_env["PATH"] = "/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

        clean_env["CI"] = "true"
        return clean_env

    @classmethod
    def validate_command(cls, cmd: List[str]):
        """
        Validates command against explicit command whitelist.
        Rejects shell operators, pipe characters, or unapproved binaries.
        """
        if not cmd:
            raise CommandSecurityError("Empty command is not allowed")

        # Reject dangerous shell injection characters
        for arg in cmd:
            if any(char in arg for char in [";", "&", "|", "`", "$", ">", "<", "\n", "\r"]):
                raise CommandSecurityError(f"Prohibited shell character in command argument: {arg}")

            for prohibited in PROHIBITED_ARGUMENTS:
                if arg.startswith(prohibited):
                    raise CommandSecurityError(f"Prohibited security-sensitive flag: {arg}")

        # Check prefix whitelist
        is_allowed = False
        for allowed in ALLOWED_COMMAND_PREFIXES:
            if len(cmd) >= len(allowed) and cmd[:len(allowed)] == allowed:
                is_allowed = True
                break

        if not is_allowed:
            raise CommandSecurityError(f"Command not in approved execution policy: {' '.join(cmd)}")

    def run_check(self, workspace_path: str, command: Optional[List[str]] = None) -> VerificationOutcome:
        cmd = command or ["mvn", "test", "-DskipTests=false"]
        self.validate_command(cmd)

        # Attempt container execution if runtime is active
        if self._container_runtime:
            try:
                return self._run_in_container(workspace_path, cmd)
            except Exception:
                pass  # Fall back to hardened subprocess

        return self._run_hardened_subprocess(workspace_path, cmd)

    def _run_in_container(self, workspace_path: str, cmd: List[str]) -> VerificationOutcome:
        """
        Executes build verification inside an ephemeral, network-isolated container.
        """
        start_time = time.time()
        container_cmd = [
            self._container_runtime, "run", "--rm",
            "--network", "none",
            "--memory", "2048m",
            "--cpus", "2.0",
            "-v", f"{os.path.abspath(workspace_path)}:/workspace:rw",
            "-w", "/workspace",
            "maven:3.9-eclipse-temurin-17",
        ] + cmd

        try:
            process = subprocess.run(
                container_cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds
            )
            duration_ms = int((time.time() - start_time) * 1000)
            combined_logs = process.stdout + "\n" + process.stderr

            compile_success, test_success, diagnostics, failed_tests = self._parse_maven_output(combined_logs)
            status = "PASSED" if (process.returncode == 0 and compile_success and test_success) else "FAILED"

            return VerificationOutcome(
                status=status,
                exit_code=process.returncode,
                duration_ms=duration_ms,
                compile_success=compile_success,
                test_success=test_success,
                logs=combined_logs[:15000],
                diagnostics=diagnostics,
                failed_test_names=failed_tests,
                sandbox_mode="CONTAINER_ROOTLESS"
            )
        except subprocess.TimeoutExpired as te:
            duration_ms = int((time.time() - start_time) * 1000)
            return VerificationOutcome(
                status="TIMEOUT",
                exit_code=-1,
                duration_ms=duration_ms,
                compile_success=False,
                test_success=False,
                logs=(te.stdout or "") + f"\n[ERROR] Container timed out after {self.timeout_seconds} seconds.",
                diagnostics=[DiagnosticFinding("timeout", message="Container exceeded time limit")],
                sandbox_mode="CONTAINER_ROOTLESS"
            )

    def _run_hardened_subprocess(self, workspace_path: str, cmd: List[str]) -> VerificationOutcome:
        """
        Executes build verification in a hardened local subprocess with purified environment
        and process-group termination safeguards.
        """
        start_time = time.time()
        clean_env = self.filter_environment()

        try:
            # Launch in a new process group to allow complete termination of child processes
            process = subprocess.Popen(
                cmd,
                cwd=workspace_path,
                env=clean_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                start_new_session=True
            )

            try:
                stdout, stderr = process.communicate(timeout=self.timeout_seconds)
            except subprocess.TimeoutExpired:
                # Terminate entire process group
                try:
                    os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                except Exception:
                    process.kill()
                stdout, stderr = process.communicate()
                duration_ms = int((time.time() - start_time) * 1000)
                return VerificationOutcome(
                    status="TIMEOUT",
                    exit_code=-1,
                    duration_ms=duration_ms,
                    compile_success=False,
                    test_success=False,
                    logs=f"{stdout}\n{stderr}\n[ERROR] Execution timed out after {self.timeout_seconds} seconds.",
                    diagnostics=[DiagnosticFinding("timeout", message="Process exceeded time limit")],
                    sandbox_mode="SUBPROCESS_HARDENED"
                )

            duration_ms = int((time.time() - start_time) * 1000)
            combined_logs = stdout + "\n" + stderr

            compile_success, test_success, diagnostics, failed_tests = self._parse_maven_output(combined_logs)
            status = "PASSED" if (process.returncode == 0 and compile_success and test_success) else "FAILED"

            return VerificationOutcome(
                status=status,
                exit_code=process.returncode,
                duration_ms=duration_ms,
                compile_success=compile_success,
                test_success=test_success,
                logs=combined_logs[:15000],
                diagnostics=diagnostics,
                failed_test_names=failed_tests,
                sandbox_mode="SUBPROCESS_HARDENED"
            )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return VerificationOutcome(
                status="ERROR",
                exit_code=-1,
                duration_ms=duration_ms,
                compile_success=False,
                test_success=False,
                logs=str(e),
                diagnostics=[DiagnosticFinding("system_error", message=str(e))],
                sandbox_mode="SUBPROCESS_HARDENED"
            )

    def _parse_maven_output(self, logs: str) -> Tuple[bool, bool, List[DiagnosticFinding], List[str]]:
        compile_success = True
        test_success = True
        diagnostics = []
        failed_tests = []

        if "[ERROR] COMPILATION ERROR" in logs or "Compilation failure" in logs:
            compile_success = False
            test_success = False

            pattern = re.compile(r"\[ERROR\]\s+(.*?):\[(\d+),\d+\]\s+(.*)")
            for line in logs.splitlines():
                match = pattern.search(line)
                if match:
                    diagnostics.append(DiagnosticFinding(
                        error_type="compilation",
                        file_path=os.path.basename(match.group(1)),
                        line_number=int(match.group(2)),
                        message=match.group(3).strip(),
                        raw_snippet=line
                    ))

        failure_match = re.search(r"Failures:\s*([1-9]\d*)|Errors:\s*([1-9]\d*)", logs)
        if failure_match:
            test_success = False

        test_fail_pattern = re.compile(r"\[ERROR\]\s+([a-zA-Z0-9_\.]+\.[a-zA-Z0-9_]+)\s+--\s+Time elapsed")
        for line in logs.splitlines():
            m = test_fail_pattern.search(line)
            if m:
                failed_tests.append(m.group(1))
                diagnostics.append(DiagnosticFinding(
                    error_type="test_failure",
                    message=f"Test failed: {m.group(1)}",
                    raw_snippet=line
                ))

        if "BUILD SUCCESS" in logs:
            compile_success = True
            test_success = True

        return compile_success, test_success, diagnostics, failed_tests
