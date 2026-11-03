"""
Manifest parser for Maven (pom.xml) and Gradle (build.gradle) files.
Extracts Java version, Spring Boot version, declared dependencies, and detects incompatibilities.
"""
import os
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

@dataclass
class DependencyCoordinates:
    group_id: str
    artifact_id: str
    version: Optional[str] = None
    scope: Optional[str] = None

@dataclass
class IncompatibleDependency:
    coordinates: str
    reason: str
    recommended_replacement: str
    rule_id: str

@dataclass
class ManifestAnalysisResult:
    build_system: str  # "maven", "gradle", or "unknown"
    java_version: Optional[str] = None
    spring_boot_version: Optional[str] = None
    dependencies: List[DependencyCoordinates] = field(default_factory=list)
    raw_properties: Dict[str, str] = field(default_factory=dict)
    has_javax_dependencies: bool = False
    has_jakarta_dependencies: bool = False
    java_version_compatible: bool = True
    spring_boot_3_compatible: bool = False
    incompatible_dependencies: List[IncompatibleDependency] = field(default_factory=list)

class ManifestParser:
    INCOMPATIBILITY_RULES = [
        {
            "match": lambda g, a: g == "javax.persistence" or a == "javax.persistence-api",
            "reason": "Java EE 8 persistence namespace is deprecated in Spring Boot 3. Use Jakarta EE 10.",
            "replacement": "jakarta.persistence:jakarta.persistence-api:3.1.0",
            "rule_id": "RULE-POM-DEPENDENCIES-SB3"
        },
        {
            "match": lambda g, a: g == "javax.servlet" or a == "javax.servlet-api",
            "reason": "Servlet 4.0 (javax.servlet) is unsupported in Spring Boot 3 (Tomcat 10 / Jetty 11 / Servlet 6.0).",
            "replacement": "jakarta.servlet:jakarta.servlet-api:6.0.0",
            "rule_id": "RULE-POM-DEPENDENCIES-SB3"
        },
        {
            "match": lambda g, a: g == "javax.validation" or a == "validation-api",
            "reason": "Bean Validation 2.0 (javax.validation) replaced by Bean Validation 3.0 (jakarta.validation).",
            "replacement": "jakarta.validation:jakarta.validation-api:3.0.2",
            "rule_id": "RULE-POM-DEPENDENCIES-SB3"
        },
        {
            "match": lambda g, a: g == "javax.annotation" or a == "javax.annotation-api",
            "reason": "Common Annotations 1.3 (javax.annotation) replaced by Jakarta Annotations 2.1.",
            "replacement": "jakarta.annotation:jakarta.annotation-api:2.1.1",
            "rule_id": "RULE-POM-DEPENDENCIES-SB3"
        }
    ]

    @classmethod
    def parse_maven_pom(cls, pom_path: str) -> ManifestAnalysisResult:
        result = ManifestAnalysisResult(build_system="maven")
        if not os.path.exists(pom_path):
            return result

        try:
            tree = ET.parse(pom_path)
            root = tree.getroot()
            ns = ""
            if root.tag.startswith("{"):
                ns = root.tag.split("}")[0] + "}"

            # Parse properties
            props_elem = root.find(f"{ns}properties")
            if props_elem is not None:
                for child in props_elem:
                    tag_name = child.tag[len(ns):] if child.tag.startswith(ns) else child.tag
                    val = (child.text or "").strip()
                    result.raw_properties[tag_name] = val

            # Detect Java version
            java_ver = (
                result.raw_properties.get("java.version")
                or result.raw_properties.get("maven.compiler.source")
                or result.raw_properties.get("maven.compiler.target")
                or result.raw_properties.get("maven.compiler.release")
            )
            result.java_version = java_ver

            # Detect Spring Boot version from properties or parent
            if "spring.boot.version" in result.raw_properties:
                result.spring_boot_version = result.raw_properties["spring.boot.version"]
            elif "spring-boot.version" in result.raw_properties:
                result.spring_boot_version = result.raw_properties["spring-boot.version"]

            parent_elem = root.find(f"{ns}parent")
            if parent_elem is not None:
                parent_art = parent_elem.find(f"{ns}artifactId")
                parent_ver = parent_elem.find(f"{ns}version")
                if parent_art is not None and "spring-boot" in (parent_art.text or ""):
                    if parent_ver is not None and not result.spring_boot_version:
                        result.spring_boot_version = parent_ver.text.strip()

            # Parse dependencies
            deps_elem = root.find(f"{ns}dependencies")
            if deps_elem is not None:
                for dep in deps_elem.findall(f"{ns}dependency"):
                    g = dep.find(f"{ns}groupId")
                    a = dep.find(f"{ns}artifactId")
                    v = dep.find(f"{ns}version")
                    s = dep.find(f"{ns}scope")

                    group_id = g.text.strip() if g is not None and g.text else ""
                    artifact_id = a.text.strip() if a is not None and a.text else ""
                    version = v.text.strip() if v is not None and v.text else None
                    if version and version.startswith("${") and version.endswith("}"):
                        prop_name = version[2:-1]
                        version = result.raw_properties.get(prop_name, version)
                    scope = s.text.strip() if s is not None and s.text else None

                    coord = DependencyCoordinates(group_id, artifact_id, version, scope)
                    result.dependencies.append(coord)

                    if "javax." in group_id or "javax." in artifact_id:
                        result.has_javax_dependencies = True
                    if "jakarta." in group_id or "jakarta." in artifact_id:
                        result.has_jakarta_dependencies = True

                    # Check incompatibility
                    coord_str = f"{group_id}:{artifact_id}" + (f":{version}" if version else "")
                    for rule in cls.INCOMPATIBILITY_RULES:
                        if rule["match"](group_id, artifact_id):
                            result.incompatible_dependencies.append(IncompatibleDependency(
                                coordinates=coord_str,
                                reason=rule["reason"],
                                recommended_replacement=rule["replacement"],
                                rule_id=rule["rule_id"]
                            ))

        except Exception:
            # Fallback regex extraction if XML malformed
            with open(pom_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            sb_match = re.search(r"<spring\.boot\.version>([0-9\.]+)<\/spring\.boot\.version>", content)
            if sb_match:
                result.spring_boot_version = sb_match.group(1)
            java_match = re.search(r"<maven\.compiler\.source>([0-9]+)<\/maven\.compiler\.source>", content)
            if java_match:
                result.java_version = java_match.group(1)
            if "javax.persistence" in content or "javax.servlet" in content:
                result.has_javax_dependencies = True

        # Check compatibility baselines
        if result.java_version:
            try:
                # Handle formats like "1.8", "8", "11", "17", "21"
                v_num = float(result.java_version) if "." in result.java_version else int(result.java_version)
                if v_num < 17 and v_num != 1.8 and v_num != 1.11:
                    result.java_version_compatible = False
                elif v_num == 1.8:
                    result.java_version_compatible = False
            except ValueError:
                pass

        if result.spring_boot_version:
            result.spring_boot_3_compatible = result.spring_boot_version.startswith("3.")

        return result

    @classmethod
    def parse_gradle_build(cls, gradle_path: str) -> ManifestAnalysisResult:
        result = ManifestAnalysisResult(build_system="gradle")
        if not os.path.exists(gradle_path):
            return result

        try:
            with open(gradle_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            sb_match = re.search(r"id\s*['\"]org\.springframework\.boot['\"]\s*version\s*['\"]([^'\"]+)['\"]", content)
            if sb_match:
                result.spring_boot_version = sb_match.group(1)
                result.spring_boot_3_compatible = result.spring_boot_version.startswith("3.")

            java_match = re.search(r"sourceCompatibility\s*=\s*['\"]?([0-9\.]+)['\"]?", content)
            if java_match:
                result.java_version = java_match.group(1)
                try:
                    v_num = float(result.java_version) if "." in result.java_version else int(result.java_version)
                    if v_num < 17 and v_num != 1.8:
                        result.java_version_compatible = False
                    elif v_num == 1.8:
                        result.java_version_compatible = False
                except ValueError:
                    pass

            if "javax." in content:
                result.has_javax_dependencies = True
            if "jakarta." in content:
                result.has_jakarta_dependencies = True

        except Exception:
            pass

        return result
