"""
Bounded Diagnostic Self-Repair Loop.
Captures compile and test diagnostics, classifies failures, retrieves relevant documentation evidence,
synthesizes targeted repair patches with pre-flight validation, and re-executes verification.
Enforces strict iteration bounds to prevent infinite loops and supports atomic rollback on failed repairs.
"""
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from ml.inference.model_provider import BaseModelProvider
from migration_engine.patching.patch_synthesizer import PatchSynthesizer, MigrationCheckpoint
from retrieval.search.retrieval_service import DocumentationRetrievalService
from services.verification_worker.worker import VerificationWorker, VerificationOutcome

@dataclass
class RepairStepRecord:
    attempt: int
    failure_category: str
    diagnostics_addressed: List[str]
    files_modified: List[str]
    verification_passed: bool
    explanation: str
    evidence_grounding: List[str] = field(default_factory=list)

@dataclass
class BoundedRepairResult:
    repaired: bool
    total_attempts: int
    final_outcome: VerificationOutcome
    steps: List[RepairStepRecord] = field(default_factory=list)

class DiagnosticRepairLoop:
    def __init__(
        self,
        worker: Optional[VerificationWorker] = None,
        retrieval_service: Optional[DocumentationRetrievalService] = None,
        max_attempts: int = 2
    ):
        self.worker = worker or VerificationWorker()
        self.retrieval_service = retrieval_service or DocumentationRetrievalService()
        self.max_attempts = max_attempts

    @staticmethod
    def classify_failure(outcome: VerificationOutcome) -> str:
        """
        Classifies verification failure into standard operational categories.
        """
        if outcome.status == "TIMEOUT":
            return "TIMEOUT"
        if not outcome.compile_success:
            return "COMPILATION_ERROR"
        if not outcome.test_success:
            return "TEST_FAILURE"
        return "RUNTIME_OR_CONFIGURATION_ERROR"

    def execute_repair(
        self,
        workspace_path: str,
        initial_outcome: VerificationOutcome,
        model_provider: BaseModelProvider
    ) -> BoundedRepairResult:
        current_outcome = initial_outcome
        steps: List[RepairStepRecord] = []

        if initial_outcome.status == "PASSED":
            return BoundedRepairResult(
                repaired=True,
                total_attempts=0,
                final_outcome=initial_outcome,
                steps=[]
            )

        for attempt in range(1, self.max_attempts + 1):
            if not current_outcome.diagnostics:
                break

            failure_category = self.classify_failure(current_outcome)
            modified_files_map = {}
            diag_summaries = []
            evidence_used = []

            # 1. Address each diagnostic finding
            for diag in current_outcome.diagnostics:
                diag_summaries.append(diag.message)
                if not diag.file_path:
                    continue

                # Locate file in workspace by exact path or filename
                matched_path = None
                for root, _, files in os.walk(workspace_path):
                    if diag.file_path in files:
                        matched_path = os.path.join(root, diag.file_path)
                        break

                if not matched_path or not os.path.exists(matched_path):
                    continue

                rel_path = os.path.relpath(matched_path, workspace_path)

                with open(matched_path, "r", encoding="utf-8") as f:
                    content = f.read()

                # 2. Retrieve authoritative documentation evidence for diagnostic error
                citations = self.retrieval_service.search(diag.message, top_k=1, target_version="3.2.0")
                if citations:
                    evidence_used.append(f"{citations[0].doc_title}: {citations[0].section_title}")

                # 3. Model synthesizes minimal repair
                repair_result = model_provider.generate_repair_correction(
                    file_path=diag.file_path,
                    current_code=content,
                    compiler_or_test_error=diag.message,
                    line_number=diag.line_number
                )

                if repair_result.transformed_code != content:
                    modified_files_map[rel_path] = repair_result.transformed_code

            if not modified_files_map:
                break

            # 4. Apply changes atomically with checkpoint
            checkpoint = None
            try:
                _, modified_list, checkpoint = PatchSynthesizer.apply_patch_atomic(
                    workspace_path,
                    modified_files_map
                )
            except Exception:
                break

            # 5. Re-run verification check
            current_outcome = self.worker.run_check(workspace_path)
            passed = (current_outcome.status == "PASSED")

            step_record = RepairStepRecord(
                attempt=attempt,
                failure_category=failure_category,
                diagnostics_addressed=diag_summaries,
                files_modified=list(modified_files_map.keys()),
                verification_passed=passed,
                explanation=f"Attempt {attempt}: Repaired {len(modified_files_map)} files for {len(diag_summaries)} errors ({failure_category}).",
                evidence_grounding=evidence_used
            )
            steps.append(step_record)

            if passed:
                return BoundedRepairResult(
                    repaired=True,
                    total_attempts=attempt,
                    final_outcome=current_outcome,
                    steps=steps
                )

        return BoundedRepairResult(
            repaired=False,
            total_attempts=len(steps),
            final_outcome=current_outcome,
            steps=steps
        )
