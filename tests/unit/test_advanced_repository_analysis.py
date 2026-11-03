import os
import tempfile
import pytest
from migration_engine.analyzers.source_analyzer import SourceAnalyzer
from migration_engine.analyzers.manifest_parser import ManifestParser

def test_incremental_analysis_and_risk_scoring():
    analyzer = SourceAnalyzer()

    java_code = """package com.example.service;

import javax.persistence.Entity;
import javax.persistence.Id;
import javax.persistence.Table;
import org.springframework.security.config.annotation.web.configuration.WebSecurityConfigurerAdapter;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;

@Entity
@Table(name = "services")
public class SecurityService extends WebSecurityConfigurerAdapter {
    @Id
    private Long id;

    protected void configure(HttpSecurity http) throws Exception {
        http.authorizeRequests().antMatchers("/public/**").permitAll();
    }
}
"""
    with tempfile.TemporaryDirectory() as tmp_dir:
        file_path = os.path.join(tmp_dir, "SecurityService.java")
        with open(file_path, "w") as f:
            f.write(java_code)

        # 1. First analysis (cache miss)
        summary1 = analyzer.analyze_repository(tmp_dir)
        assert summary1.total_files == 1
        assert summary1.cached_files_count == 0
        assert "SecurityService.java" in summary1.files

        fa1 = summary1.files["SecurityService.java"]
        assert fa1.risk_level in ["HIGH", "CRITICAL"]
        assert fa1.risk_score >= 40.0
        assert "WebSecurityConfigurerAdapter" in fa1.deprecated_spring_apis
        assert any(s.rule_id == "RULE-SPRING-SECURITY-6-FILTER" for s in fa1.migration_sites)
        assert any(s.rule_id == "RULE-JAKARTA-EE-PERSISTENCE" for s in fa1.migration_sites)

        # 2. Second analysis on unchanged files (cache hit)
        summary2 = analyzer.analyze_repository(tmp_dir)
        assert summary2.cached_files_count == 1
        assert summary2.files["SecurityService.java"].risk_score == fa1.risk_score

        # Verify dependency impact graph structure
        assert "nodes" in summary2.dependency_impact_graph
        assert "SecurityService.java" in summary2.dependency_impact_graph["nodes"]

def test_manifest_incompatibility_detection():
    pom_content = """<project xmlns="http://maven.apache.org/POM/4.0.0">
    <modelVersion>4.0.0</modelVersion>
    <groupId>com.example</groupId>
    <artifactId>legacy-service</artifactId>
    <version>1.0.0</version>
    <properties>
        <java.version>11</java.version>
        <spring.boot.version>2.7.18</spring.boot.version>
    </properties>
    <dependencies>
        <dependency>
            <groupId>javax.persistence</groupId>
            <artifactId>javax.persistence-api</artifactId>
            <version>2.2</version>
        </dependency>
        <dependency>
            <groupId>javax.servlet</groupId>
            <artifactId>javax.servlet-api</artifactId>
            <version>4.0.1</version>
        </dependency>
    </dependencies>
</project>"""

    with tempfile.NamedTemporaryFile(suffix=".xml", mode="w", delete=False) as f:
        f.write(pom_content)
        temp_pom = f.name

    try:
        manifest = ManifestParser.parse_maven_pom(temp_pom)
        assert manifest.java_version == "11"
        assert not manifest.java_version_compatible, "Java 11 should be flagged as incompatible with Spring Boot 3"
        assert manifest.spring_boot_version == "2.7.18"
        assert not manifest.spring_boot_3_compatible
        assert len(manifest.incompatible_dependencies) >= 2
        incompatible_coords = [d.coordinates for d in manifest.incompatible_dependencies]
        assert any("javax.persistence" in c for c in incompatible_coords)
        assert any("javax.servlet" in c for c in incompatible_coords)
    finally:
        if os.path.exists(temp_pom):
            os.remove(temp_pom)

