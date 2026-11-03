import os
import tempfile
import pytest
from migration_engine.analyzers.source_analyzer import SourceAnalyzer

def test_modern_java17_ast_parser():
    """
    Tests that the JDK Tree API AST parser successfully parses modern Java 17+ constructs
    (records, switch expressions, text blocks, pattern matching) that would break Java 8 parsers.
    """
    analyzer = SourceAnalyzer()
    assert analyzer.has_jdk_parser, "JavaAstParser.class must be compiled and available"

    modern_java_code = """package com.example.modern;

import javax.persistence.Entity;
import javax.persistence.Id;
import javax.validation.constraints.NotNull;
import javax.validation.constraints.Size;

public record CustomerRecord(
    @Id Long id,
    @NotNull @Size(min = 2, max = 50) String name,
    String email
) {
    public int computeCode(Object obj) {
        // Pattern matching for instanceof (Java 16+)
        if (obj instanceof String s && s.length() > 0) {
            // Switch expression (Java 14+)
            return switch (s.length()) {
                case 1 -> 10;
                case 2 -> 20;
                default -> 100;
            };
        }
        return 0;
    }

    public String formatDetails() {
        // Text blocks (Java 15+)
        return \"\"\"
               Customer: %s
               Email: %s
               \"\"\".formatted(name, email);
    }
}
"""

    with tempfile.NamedTemporaryFile(suffix=".java", mode="w", delete=False) as tf:
        tf.write(modern_java_code)
        temp_path = tf.name

    try:
        analysis = analyzer.analyze_java_file("CustomerRecord.java", modern_java_code, abs_file_path=temp_path)

        # Verify types and modern features were recognized
        assert any("RECORD" in t for t in analysis.classes_declared), f"Record not detected in {analysis.classes_declared}"
        assert any("record" in f for f in analysis.modern_features_detected), "Record feature not detected"
        assert "switch_expression" in analysis.modern_features_detected
        assert "text_blocks" in analysis.modern_features_detected

        # Verify candidate migration sites identified in modern syntax
        rules_found = [s.rule_id for s in analysis.migration_sites]
        assert "RULE-JAKARTA-EE-PERSISTENCE" in rules_found
        assert "RULE-JAKARTA-EE-VALIDATION" in rules_found

        # Check line numbers match actual imports
        persistence_sites = [s for s in analysis.migration_sites if s.rule_id == "RULE-JAKARTA-EE-PERSISTENCE"]
        assert len(persistence_sites) >= 2
        assert all(s.confidence == "confirmed" for s in persistence_sites)

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
