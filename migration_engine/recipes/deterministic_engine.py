"""
Deterministic Migration Engine (OpenRewrite-compatible baseline).
Applies rule-based transformations to Java files, Maven pom.xml files, and properties.
Ensures idempotency so already-migrated content is preserved without duplicate modifications.
"""
import difflib
import os
import re
from typing import Dict, List, Tuple, Any
from migration_engine.recipes.rule_registry import MIGRATION_RULES, MigrationRule

class DeterministicMigrationEngine:
    def __init__(self, rules: List[MigrationRule] = None):
        self.rules = rules or list(MIGRATION_RULES.values())

    def transform_content(self, relative_path: str, content: str) -> Tuple[str, List[str]]:
        """
        Applies applicable rules to file content based on file extension and pattern matching.
        Idempotent: if content is already in the migrated state, no changes are produced.
        Returns (transformed_content, applied_rule_ids).
        """
        applied_rule_ids = []
        new_content = content

        for rule in self.rules:
            # Java files: namespace and api signature rules
            if relative_path.endswith(".java") and rule.category.value in ["namespace", "security", "api_signature"]:
                rule_applied = False
                for old_val, new_val in rule.replacement_mapping.items():
                    if old_val in new_content:
                        new_content = new_content.replace(old_val, new_val)
                        rule_applied = True
                if rule_applied and rule.rule_id not in applied_rule_ids:
                    applied_rule_ids.append(rule.rule_id)

            # Maven pom.xml files: dependency and parent upgrades
            elif relative_path.endswith("pom.xml") and rule.category.value == "dependency":
                rule_applied = False
                # Handle generic 2.x spring boot version tags
                sb_ver_match = re.search(r"<spring\.boot\.version>2\.[0-9]+\.[0-9]+<\/spring\.boot\.version>", new_content)
                if sb_ver_match:
                    new_content = new_content.replace(sb_ver_match.group(0), "<spring.boot.version>3.2.0</spring.boot.version>")
                    rule_applied = True

                for old_val, new_val in rule.replacement_mapping.items():
                    if old_val in new_content:
                        new_content = new_content.replace(old_val, new_val)
                        rule_applied = True

                if rule_applied and rule.rule_id not in applied_rule_ids:
                    applied_rule_ids.append(rule.rule_id)

            # Configuration properties / YAML
            elif (relative_path.endswith(".properties") or relative_path.endswith(".yml") or relative_path.endswith(".yaml")) and rule.category.value == "configuration":
                rule_applied = False
                for old_val, new_val in rule.replacement_mapping.items():
                    if old_val in new_content:
                        new_content = new_content.replace(old_val, new_val)
                        rule_applied = True
                if rule_applied and rule.rule_id not in applied_rule_ids:
                    applied_rule_ids.append(rule.rule_id)

        return new_content, applied_rule_ids

    def generate_diff(self, file_path: str, original: str, modified: str) -> str:
        orig_lines = original.splitlines(keepends=True)
        mod_lines = modified.splitlines(keepends=True)
        diff = difflib.unified_diff(
            orig_lines,
            mod_lines,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
            lineterm=""
        )
        return "".join(diff)

    def migrate_directory(self, root_dir: str) -> Dict[str, Any]:
        """
        Executes deterministic migration across all files in root_dir.
        Returns summary of modified files, diffs, and applied rules.
        """
        results = {
            "changed_files": [],
            "diffs": {},
            "applied_rules": set(),
            "total_files_analyzed": 0,
            "total_files_modified": 0,
        }

        for dirpath, _, filenames in os.walk(root_dir):
            if any(part.startswith(".") or part in ["target", "build", "node_modules", ".git", ".venv"] for part in dirpath.split(os.sep)):
                continue

            for fname in sorted(filenames):
                if not (fname.endswith(".java") or fname.endswith(".properties") or fname.endswith(".yml") or fname.endswith(".yaml") or fname.endswith(".xml")):
                    continue

                full_path = os.path.join(dirpath, fname)
                rel_path = os.path.relpath(full_path, root_dir)
                results["total_files_analyzed"] += 1

                try:
                    with open(full_path, "r", encoding="utf-8") as f:
                        original_content = f.read()
                except UnicodeDecodeError:
                    continue

                new_content, applied_rules = self.transform_content(rel_path, original_content)
                if new_content != original_content:
                    diff_text = self.generate_diff(rel_path, original_content, new_content)
                    results["changed_files"].append(rel_path)
                    results["diffs"][rel_path] = diff_text
                    results["applied_rules"].update(applied_rules)

                    # Update the file on disk in the worktree
                    with open(full_path, "w", encoding="utf-8") as f:
                        f.write(new_content)

        results["total_files_modified"] = len(results["changed_files"])
        results["applied_rules"] = list(results["applied_rules"])
        return results
