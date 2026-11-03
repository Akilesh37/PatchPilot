import hashlib
import json
import os
import re
import subprocess
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Any, Tuple
import javalang

@dataclass
class MigrationSite:
    file_path: str
    line_number: int
    rule_id: str
    pattern_matched: str
    line_content: str
    confidence: str  # "confirmed" or "heuristic"
    context_snippet: str = ""

@dataclass
class FileAnalysis:
    relative_path: str
    file_type: str  # "java", "properties", "yaml", "xml", "other"
    sha256_hash: str
    line_count: int
    migration_sites: List[MigrationSite] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    classes_declared: List[str] = field(default_factory=list)
    interfaces_declared: List[str] = field(default_factory=list)
    methods_declared: List[str] = field(default_factory=list)
    fields_declared: List[str] = field(default_factory=list)
    annotations_detected: List[str] = field(default_factory=list)
    modern_features_detected: List[str] = field(default_factory=list)
    deprecated_spring_apis: List[str] = field(default_factory=list)
    package_name: str = ""
    risk_score: float = 0.0
    risk_level: str = "LOW"  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    downstream_impacts: List[str] = field(default_factory=list)

@dataclass
class DependencyNode:
    file_path: str
    file_type: str
    risk_level: str
    risk_score: float
    classes: List[str]
    imports: List[str]
    rules_detected: List[str]

@dataclass
class DependencyImpactGraph:
    nodes: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    edges: List[Dict[str, str]] = field(default_factory=list)  # {"source": fileA, "target": fileB, "type": "imports"}
    impact_chains: Dict[str, List[str]] = field(default_factory=dict)

@dataclass
class RepositoryAnalysisSummary:
    root_path: str
    commit_or_dir_hash: str
    total_files: int
    java_files_count: int
    total_migration_sites: int
    affected_files_count: int
    rules_detected: Set[str] = field(default_factory=set)
    files: Dict[str, FileAnalysis] = field(default_factory=dict)
    file_dependency_graph: Dict[str, List[str]] = field(default_factory=dict)
    unsupported_patterns: List[str] = field(default_factory=list)
    dependency_impact_graph: Dict[str, Any] = field(default_factory=dict)
    average_risk_score: float = 0.0
    high_risk_files: List[str] = field(default_factory=list)
    cached_files_count: int = 0

class SourceAnalyzer:
    """
    Advanced Repository Source Analyzer.
    Features:
    - High-fidelity JDK 17+ Compiler Tree API analysis
    - Fallback javalang AST parsing
    - Package, class, interface, method, field, and annotation extraction
    - Deprecated Spring API detection
    - Java version compatibility inspection
    - Incremental analysis cache using SHA-256 content hashes
    - Multi-factor file-level migration risk scoring
    - Structured cross-file dependency and downstream impact graph
    """
    def __init__(self):
        self.parser_class_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "."))
        self.has_jdk_parser = os.path.exists(os.path.join(self.parser_class_dir, "tools", "JavaAstParser.class"))
        # In-memory incremental cache: {relative_path: (sha256_hash, FileAnalysis)}
        self._cache: Dict[str, Tuple[str, FileAnalysis]] = {}

    @staticmethod
    def compute_sha256(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def _parse_with_jdk_tree_api(self, abs_file_path: str) -> Optional[dict]:
        if not self.has_jdk_parser or not os.path.exists(abs_file_path):
            return None
        try:
            res = subprocess.run(
                ["java", "-cp", self.parser_class_dir, "tools.JavaAstParser", abs_file_path],
                capture_output=True,
                text=True,
                timeout=10
            )
            if res.returncode == 0 and res.stdout.strip().startswith("{"):
                return json.loads(res.stdout)
        except Exception:
            pass
        return None

    def calculate_risk(self, sites: List[MigrationSite], deprecated_apis: List[str], line_count: int) -> Tuple[float, str]:
        """
        Calculates migration risk score (0.0 to 100.0) and assigns risk level.
        Factors:
        - Deprecated architectural APIs (e.g. WebSecurityConfigurerAdapter) add high risk (+40 each)
        - Security / Filter changes (+30)
        - Persistence namespace shifts (+10 per distinct site, capped at 30)
        - Code size multiplier
        """
        score = 0.0

        if deprecated_apis:
            score += len(deprecated_apis) * 35.0

        for site in sites:
            if "SECURITY" in site.rule_id:
                score += 25.0
            elif "PERSISTENCE" in site.rule_id:
                score += 8.0
            elif "SERVLET" in site.rule_id:
                score += 15.0
            elif "CONFIG" in site.rule_id:
                score += 5.0
            else:
                score += 5.0

        if line_count > 300:
            score *= 1.2

        score = min(round(score, 1), 100.0)

        if score >= 70.0:
            level = "CRITICAL"
        elif score >= 40.0:
            level = "HIGH"
        elif score >= 15.0:
            level = "MEDIUM"
        else:
            level = "LOW"

        return score, level

    def analyze_java_file(self, relative_path: str, content: str, abs_file_path: Optional[str] = None) -> FileAnalysis:
        content_hash = self.compute_sha256(content)

        # Check incremental cache
        if relative_path in self._cache:
            cached_hash, cached_analysis = self._cache[relative_path]
            if cached_hash == content_hash:
                return cached_analysis

        lines = content.splitlines()
        file_analysis = FileAnalysis(
            relative_path=relative_path,
            file_type="java",
            sha256_hash=content_hash,
            line_count=len(lines)
        )

        # 1. Primary: Standard JDK Tree API parser
        if abs_file_path:
            jdk_data = self._parse_with_jdk_tree_api(abs_file_path)
            if jdk_data:
                file_analysis.package_name = jdk_data.get("packageName", "")
                file_analysis.imports = jdk_data.get("imports", [])
                file_analysis.classes_declared = jdk_data.get("types", [])
                file_analysis.interfaces_declared = jdk_data.get("interfaces", [])
                file_analysis.methods_declared = jdk_data.get("methods", [])
                file_analysis.fields_declared = jdk_data.get("fields", [])
                file_analysis.annotations_detected = jdk_data.get("annotations", [])
                file_analysis.modern_features_detected = jdk_data.get("modernFeatures", [])
                file_analysis.deprecated_spring_apis = jdk_data.get("deprecatedSpringApis", [])

                for s in jdk_data.get("migrationSites", []):
                    line_no = s.get("lineNumber", 1)
                    file_analysis.migration_sites.append(MigrationSite(
                        file_path=relative_path,
                        line_number=line_no,
                        rule_id=s.get("ruleId", ""),
                        pattern_matched=s.get("patternMatched", ""),
                        line_content=s.get("lineContent", ""),
                        confidence=s.get("confidence", "confirmed"),
                        context_snippet=self._get_snippet(lines, line_no)
                    ))

                score, level = self.calculate_risk(
                    file_analysis.migration_sites,
                    file_analysis.deprecated_spring_apis,
                    file_analysis.line_count
                )
                file_analysis.risk_score = score
                file_analysis.risk_level = level

                self._cache[relative_path] = (content_hash, file_analysis)
                return file_analysis

        # 2. Fallback AST parsing with javalang
        ast_tree = None
        try:
            ast_tree = javalang.parse.parse(content)
        except Exception:
            pass

        if ast_tree:
            if hasattr(ast_tree, "package") and ast_tree.package:
                file_analysis.package_name = ast_tree.package.name
            if hasattr(ast_tree, "imports") and ast_tree.imports:
                for imp in ast_tree.imports:
                    file_analysis.imports.append(imp.path)

            for _, node in ast_tree.filter(javalang.tree.ClassDeclaration):
                file_analysis.classes_declared.append(node.name)
                if node.extends and "WebSecurityConfigurerAdapter" in str(node.extends.name):
                    file_analysis.deprecated_spring_apis.append("WebSecurityConfigurerAdapter")

            for _, node in ast_tree.filter(javalang.tree.InterfaceDeclaration):
                file_analysis.interfaces_declared.append(node.name)

            for _, node in ast_tree.filter(javalang.tree.MethodDeclaration):
                file_analysis.methods_declared.append(node.name)

            for _, node in ast_tree.filter(javalang.tree.FieldDeclaration):
                for declarator in node.declarators:
                    file_analysis.fields_declared.append(declarator.name)

        # 3. Rule inspection across source lines
        for idx, line in enumerate(lines, 1):
            stripped = line.strip()

            if "javax.persistence." in stripped:
                confidence = "confirmed" if stripped.startswith("import ") or "@" in stripped else "heuristic"
                file_analysis.migration_sites.append(MigrationSite(
                    file_path=relative_path,
                    line_number=idx,
                    rule_id="RULE-JAKARTA-EE-PERSISTENCE",
                    pattern_matched="javax.persistence.",
                    line_content=stripped,
                    confidence=confidence,
                    context_snippet=self._get_snippet(lines, idx)
                ))

            if "javax.servlet." in stripped:
                confidence = "confirmed" if stripped.startswith("import ") or "HttpServlet" in stripped else "heuristic"
                file_analysis.migration_sites.append(MigrationSite(
                    file_path=relative_path,
                    line_number=idx,
                    rule_id="RULE-JAKARTA-EE-SERVLET",
                    pattern_matched="javax.servlet.",
                    line_content=stripped,
                    confidence=confidence,
                    context_snippet=self._get_snippet(lines, idx)
                ))

            if "javax.validation." in stripped:
                confidence = "confirmed" if stripped.startswith("import ") or "@" in stripped else "heuristic"
                file_analysis.migration_sites.append(MigrationSite(
                    file_path=relative_path,
                    line_number=idx,
                    rule_id="RULE-JAKARTA-EE-VALIDATION",
                    pattern_matched="javax.validation.",
                    line_content=stripped,
                    confidence=confidence,
                    context_snippet=self._get_snippet(lines, idx)
                ))

            if "javax.annotation." in stripped:
                confidence = "confirmed" if stripped.startswith("import ") or "@" in stripped else "heuristic"
                file_analysis.migration_sites.append(MigrationSite(
                    file_path=relative_path,
                    line_number=idx,
                    rule_id="RULE-JAKARTA-EE-ANNOTATION",
                    pattern_matched="javax.annotation.",
                    line_content=stripped,
                    confidence=confidence,
                    context_snippet=self._get_snippet(lines, idx)
                ))

            if "WebSecurityConfigurerAdapter" in stripped or "authorizeRequests()" in stripped or "antMatchers(" in stripped:
                if "WebSecurityConfigurerAdapter" not in file_analysis.deprecated_spring_apis:
                    file_analysis.deprecated_spring_apis.append("WebSecurityConfigurerAdapter")
                file_analysis.migration_sites.append(MigrationSite(
                    file_path=relative_path,
                    line_number=idx,
                    rule_id="RULE-SPRING-SECURITY-6-FILTER",
                    pattern_matched="Spring Security 5 deprecation",
                    line_content=stripped,
                    confidence="confirmed",
                    context_snippet=self._get_snippet(lines, idx)
                ))

        score, level = self.calculate_risk(
            file_analysis.migration_sites,
            file_analysis.deprecated_spring_apis,
            file_analysis.line_count
        )
        file_analysis.risk_score = score
        file_analysis.risk_level = level

        self._cache[relative_path] = (content_hash, file_analysis)
        return file_analysis

    def analyze_properties_file(self, relative_path: str, content: str) -> FileAnalysis:
        content_hash = self.compute_sha256(content)
        if relative_path in self._cache and self._cache[relative_path][0] == content_hash:
            return self._cache[relative_path][1]

        lines = content.splitlines()
        file_analysis = FileAnalysis(
            relative_path=relative_path,
            file_type="properties",
            sha256_hash=content_hash,
            line_count=len(lines)
        )

        for idx, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue

            if "spring.redis." in stripped:
                file_analysis.migration_sites.append(MigrationSite(
                    file_path=relative_path,
                    line_number=idx,
                    rule_id="RULE-CONFIG-REDIS-PREFIX",
                    pattern_matched="spring.redis.",
                    line_content=stripped,
                    confidence="confirmed",
                    context_snippet=self._get_snippet(lines, idx)
                ))

            if "server.max-http-header-size" in stripped:
                file_analysis.migration_sites.append(MigrationSite(
                    file_path=relative_path,
                    line_number=idx,
                    rule_id="RULE-CONFIG-MAX-HTTP-HEADER",
                    pattern_matched="server.max-http-header-size",
                    line_content=stripped,
                    confidence="confirmed",
                    context_snippet=self._get_snippet(lines, idx)
                ))

        score, level = self.calculate_risk(file_analysis.migration_sites, [], file_analysis.line_count)
        file_analysis.risk_score = score
        file_analysis.risk_level = level

        self._cache[relative_path] = (content_hash, file_analysis)
        return file_analysis

    def analyze_pom_file(self, relative_path: str, content: str) -> FileAnalysis:
        content_hash = self.compute_sha256(content)
        if relative_path in self._cache and self._cache[relative_path][0] == content_hash:
            return self._cache[relative_path][1]

        lines = content.splitlines()
        file_analysis = FileAnalysis(
            relative_path=relative_path,
            file_type="xml",
            sha256_hash=content_hash,
            line_count=len(lines)
        )

        for idx, line in enumerate(lines, 1):
            stripped = line.strip()
            if "<spring.boot.version>2." in stripped or "javax.persistence-api" in stripped or "javax.servlet-api" in stripped or "javax.annotation-api" in stripped or "validation-api" in stripped:
                file_analysis.migration_sites.append(MigrationSite(
                    file_path=relative_path,
                    line_number=idx,
                    rule_id="RULE-POM-DEPENDENCIES-SB3",
                    pattern_matched=stripped,
                    line_content=stripped,
                    confidence="confirmed",
                    context_snippet=self._get_snippet(lines, idx)
                ))

        score, level = self.calculate_risk(file_analysis.migration_sites, [], file_analysis.line_count)
        file_analysis.risk_score = score
        file_analysis.risk_level = level

        self._cache[relative_path] = (content_hash, file_analysis)
        return file_analysis

    def build_impact_graph(self, files_dict: Dict[str, FileAnalysis]) -> DependencyImpactGraph:
        """
        Builds a cross-file dependency and downstream impact graph.
        Links files based on declared packages, classes, and imported package types.
        Computes transitive impact chains when a high-risk file changes.
        """
        graph = DependencyImpactGraph()

        # Map declared class names to defining relative file path
        class_to_file: Dict[str, str] = {}
        for rpath, fa in files_dict.items():
            for c in fa.classes_declared:
                class_name = c.split(" ")[0]  # strip " (CLASS)" or " (RECORD)"
                class_to_file[class_name] = rpath

            graph.nodes[rpath] = {
                "file_path": rpath,
                "file_type": fa.file_type,
                "risk_level": fa.risk_level,
                "risk_score": fa.risk_score,
                "line_count": fa.line_count,
                "migration_sites_count": len(fa.migration_sites),
                "rules_detected": list(set(s.rule_id for s in fa.migration_sites)),
                "classes": fa.classes_declared,
                "package": fa.package_name
            }

        # Build edges from imports
        for rpath, fa in files_dict.items():
            downstream = []
            for imp in fa.imports:
                for cls_name, defining_path in class_to_file.items():
                    if defining_path != rpath and (imp.endswith("." + cls_name) or imp == cls_name):
                        graph.edges.append({
                            "source": rpath,
                            "target": defining_path,
                            "type": "imports"
                        })
                        if rpath not in files_dict[defining_path].downstream_impacts:
                            files_dict[defining_path].downstream_impacts.append(rpath)

        # Compute impact chains
        for rpath, fa in files_dict.items():
            if fa.downstream_impacts:
                graph.impact_chains[rpath] = fa.downstream_impacts

        return graph

    def analyze_repository(self, repo_dir: str) -> RepositoryAnalysisSummary:
        total_files = 0
        java_count = 0
        all_sites_count = 0
        affected_files = 0
        rules_found = set()
        files_dict: Dict[str, FileAnalysis] = {}
        dep_graph: Dict[str, List[str]] = {}
        cached_count = 0

        hasher = hashlib.sha256()

        for dirpath, _, filenames in os.walk(repo_dir):
            if any(part.startswith(".") or part in ["target", "build", "node_modules", ".git", ".venv"] for part in dirpath.split(os.sep)):
                continue

            for fname in sorted(filenames):
                full_path = os.path.join(dirpath, fname)
                rel_path = os.path.relpath(full_path, repo_dir)
                total_files += 1

                try:
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                except Exception:
                    continue

                hasher.update(content.encode("utf-8"))

                # Check if file was cached
                c_hash = self.compute_sha256(content)
                is_cached = (rel_path in self._cache and self._cache[rel_path][0] == c_hash)
                if is_cached:
                    cached_count += 1

                analysis = None
                if fname.endswith(".java"):
                    java_count += 1
                    analysis = self.analyze_java_file(rel_path, content, abs_file_path=full_path)
                    dep_graph[rel_path] = [imp for imp in analysis.imports if not imp.startswith("java.")]
                elif fname.endswith(".properties") or fname.endswith(".yml") or fname.endswith(".yaml"):
                    analysis = self.analyze_properties_file(rel_path, content)
                elif fname == "pom.xml":
                    analysis = self.analyze_pom_file(rel_path, content)
                else:
                    analysis = FileAnalysis(
                        relative_path=rel_path,
                        file_type="other",
                        sha256_hash=c_hash,
                        line_count=len(content.splitlines())
                    )

                if analysis:
                    files_dict[rel_path] = analysis
                    if analysis.migration_sites:
                        affected_files += 1
                        all_sites_count += len(analysis.migration_sites)
                        for site in analysis.migration_sites:
                            rules_found.add(site.rule_id)

        # Build cross-file dependency impact graph
        impact_graph = self.build_impact_graph(files_dict)

        # Compute average risk and find high-risk files
        scores = [f.risk_score for f in files_dict.values() if f.migration_sites]
        avg_risk = round(sum(scores) / len(scores), 2) if scores else 0.0
        high_risk = [f.relative_path for f in files_dict.values() if f.risk_level in ["HIGH", "CRITICAL"]]

        summary = RepositoryAnalysisSummary(
            root_path=repo_dir,
            commit_or_dir_hash=hasher.hexdigest(),
            total_files=total_files,
            java_files_count=java_count,
            total_migration_sites=all_sites_count,
            affected_files_count=affected_files,
            rules_detected=rules_found,
            files=files_dict,
            file_dependency_graph=dep_graph,
            unsupported_patterns=[],
            dependency_impact_graph={
                "nodes": impact_graph.nodes,
                "edges": impact_graph.edges,
                "impact_chains": impact_graph.impact_chains
            },
            average_risk_score=avg_risk,
            high_risk_files=high_risk,
            cached_files_count=cached_count
        )
        return summary

    def _get_snippet(self, lines: List[str], line_num: int, context_lines: int = 2) -> str:
        start = max(0, line_num - 1 - context_lines)
        end = min(len(lines), line_num + context_lines)
        snippet_lines = []
        for i in range(start, end):
            prefix = " > " if i == (line_num - 1) else "   "
            snippet_lines.append(f"{i+1:3d}{prefix}{lines[i]}")
        return "\n".join(snippet_lines)
