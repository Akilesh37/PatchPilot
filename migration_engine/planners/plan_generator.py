"""
Migration Planner.
Generates an evidence-grounded, structured migration plan prior to patch synthesis.
Every operation is fully specified with rule ID, coordinates, deterministic vs contextual typing,
rationale, evidence, risk, verification criteria, and rollback metadata.
Enforces idempotency detection so already-migrated patterns are recognized as no-ops.
"""
import uuid
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from migration_engine.analyzers.source_analyzer import RepositoryAnalysisSummary
from migration_engine.recipes.rule_registry import MIGRATION_RULES, MigrationRule
from retrieval.search.retrieval_service import DocumentationRetrievalService, Citation

@dataclass
class MigrationOperation:
    operation_id: str
    rule_id: str
    file_path: str
    line_start: int
    line_end: int
    original_snippet: str
    proposed_modification: str
    transformation_type: str  # "DETERMINISTIC" or "LLM_CONTEXTUAL"
    rationale: str
    documentation_evidence: Dict[str, Any]
    risk_classification: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    verification_requirements: List[str]
    rollback_action: Dict[str, Any]
    is_idempotent_noop: bool = False

@dataclass
class StructuredMigrationPlan:
    goal: str
    affected_files: List[str]
    applicable_rule_ids: List[str]
    evidence_references: List[Dict[str, Any]]
    risks: List[str]
    validation_steps: List[str]
    ambiguities: List[str]
    operations: List[MigrationOperation] = field(default_factory=list)
    total_operations_count: int = 0
    deterministic_count: int = 0
    contextual_count: int = 0
    idempotent_noop_count: int = 0

class MigrationPlanGenerator:
    def __init__(self, retrieval_service: Optional[DocumentationRetrievalService] = None):
        self.retrieval_service = retrieval_service or DocumentationRetrievalService()

    def generate_plan(
        self,
        analysis: RepositoryAnalysisSummary,
        source_version: str = "2.7.18",
        target_version: str = "3.2.0"
    ) -> StructuredMigrationPlan:
        affected_files = sorted(list(set([
            f.relative_path for f in analysis.files.values() if f.migration_sites
        ])))

        rule_ids = sorted(list(analysis.rules_detected))
        evidence_citations: List[Dict[str, Any]] = []
        citations_by_rule: Dict[str, Dict[str, Any]] = {}

        # 1. Retrieve authoritative documentation evidence for each detected rule
        for rid in rule_ids:
            rule = MIGRATION_RULES.get(rid)
            if rule:
                query = f"{rule.title} {rule.description}"
                citations = self.retrieval_service.search(query, top_k=2, target_version=target_version)
                if citations:
                    c = citations[0]
                    citation_dict = {
                        "rule_id": rid,
                        "doc_title": c.doc_title,
                        "section_title": c.section_title,
                        "canonical_url": c.canonical_url,
                        "snippet": c.snippet,
                        "target_version": c.target_version,
                        "provenance": c.provenance,
                        "score": round(c.score, 4)
                    }
                    evidence_citations.append(citation_dict)
                    citations_by_rule[rid] = citation_dict

                    for extra_c in citations[1:]:
                        evidence_citations.append({
                            "rule_id": rid,
                            "doc_title": extra_c.doc_title,
                            "section_title": extra_c.section_title,
                            "canonical_url": extra_c.canonical_url,
                            "snippet": extra_c.snippet,
                            "target_version": extra_c.target_version,
                            "provenance": extra_c.provenance,
                            "score": round(extra_c.score, 4)
                        })

        # 2. Build structured MigrationOperations
        operations: List[MigrationOperation] = []
        deterministic_cnt = 0
        contextual_cnt = 0
        noop_cnt = 0

        for rpath, fa in analysis.files.items():
            for site in fa.migration_sites:
                rule = MIGRATION_RULES.get(site.rule_id)
                evidence = citations_by_rule.get(site.rule_id, {
                    "rule_id": site.rule_id,
                    "doc_title": rule.title if rule else "Framework Migration Guide",
                    "canonical_url": rule.doc_url if rule else "",
                    "snippet": rule.description if rule else ""
                })

                # Determine transformation type
                is_deterministic = rule.is_deterministic if rule else True
                transformation_type = "DETERMINISTIC" if is_deterministic else "LLM_CONTEXTUAL"

                # Check proposed modification
                proposed_code = site.line_content
                if rule and rule.replacement_mapping:
                    for old_v, new_v in rule.replacement_mapping.items():
                        if old_v in proposed_code:
                            proposed_code = proposed_code.replace(old_v, new_v)

                # Check idempotency: is the line already in the target state?
                is_noop = (proposed_code == site.line_content)
                if is_noop:
                    noop_cnt += 1
                else:
                    if is_deterministic:
                        deterministic_cnt += 1
                    else:
                        contextual_cnt += 1

                # Risk level from rule and site
                if "SECURITY" in site.rule_id:
                    risk_class = "HIGH"
                elif "SERVLET" in site.rule_id:
                    risk_class = "MEDIUM"
                elif "POM" in site.rule_id:
                    risk_class = "MEDIUM"
                else:
                    risk_class = "LOW"

                op = MigrationOperation(
                    operation_id=f"op-{site.rule_id.lower()}-{uuid.uuid4().hex[:6]}",
                    rule_id=site.rule_id,
                    file_path=rpath,
                    line_start=site.line_number,
                    line_end=site.line_number,
                    original_snippet=site.line_content,
                    proposed_modification=proposed_code,
                    transformation_type=transformation_type,
                    rationale=rule.description if rule else "Spring Boot 3 migration requirement",
                    documentation_evidence=evidence,
                    risk_classification=risk_class,
                    verification_requirements=rule.required_validation_tests if rule else ["mvn test-compile"],
                    rollback_action={
                        "strategy": "REVERSE_STRING_REPLACE" if is_deterministic else "RESTORE_FILE_SNAPSHOT",
                        "original_content": site.line_content,
                        "file_sha256": fa.sha256_hash
                    },
                    is_idempotent_noop=is_noop
                )
                operations.append(op)

        # 3. Overall risks and validation steps
        risks = []
        if any("javax.servlet" in r for r in rule_ids):
            risks.append("Binary breaking changes in Servlet 6.0: verify third-party servlet filter libraries.")
        if any("SECURITY" in r for r in rule_ids):
            risks.append("Spring Security 6 enforces strict authorization rules: ensure all public endpoints are explicitly configured.")
        if not analysis.java_files_count:
            risks.append("No Java files detected: verification may not execute compile checks.")
        if any(f.risk_level in ["HIGH", "CRITICAL"] for f in analysis.files.values()):
            risks.append("High-risk architectural components detected (e.g. security configuration): manual review recommended.")

        validation_steps = [
            "Execute Maven compile with JDK 17+ baseline (`mvn test-compile`)",
            "Run unit and integration test suite (`mvn test`)",
            "Verify entity-relation bindings under jakarta.persistence",
            "Inspect migrated configuration properties for deprecated keys"
        ]

        ambiguities = []
        if analysis.unsupported_patterns:
            for pat in analysis.unsupported_patterns:
                ambiguities.append(f"Ambiguous pattern detected: {pat} requires developer review.")

        goal = f"Migrate repository from Spring Boot {source_version} to Spring Boot {target_version} addressing {len(analysis.rules_detected)} detected migration rules across {len(affected_files)} affected files."

        return StructuredMigrationPlan(
            goal=goal,
            affected_files=affected_files,
            applicable_rule_ids=rule_ids,
            evidence_references=evidence_citations,
            risks=risks,
            validation_steps=validation_steps,
            ambiguities=ambiguities,
            operations=operations,
            total_operations_count=len(operations),
            deterministic_count=deterministic_cnt,
            contextual_count=contextual_cnt,
            idempotent_noop_count=noop_cnt
        )
