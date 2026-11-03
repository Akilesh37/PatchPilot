"""
Structured, versioned Migration Rule Registry for Spring Boot 2.x to 3.x migrations.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional

class RuleCategory(str, Enum):
    NAMESPACE = "namespace"
    DEPENDENCY = "dependency"
    CONFIGURATION = "configuration"
    SECURITY = "security"
    API_SIGNATURE = "api_signature"

class RuleConfidence(str, Enum):
    CONFIRMED = "confirmed"
    HEURISTIC = "heuristic"
    EXPERIMENTAL = "experimental"

@dataclass
class MigrationRule:
    rule_id: str
    title: str
    category: RuleCategory
    source_version_constraint: str  # e.g., ">=2.0.0, <3.0.0"
    target_version_constraint: str  # e.g., ">=3.0.0"
    description: str
    affected_pattern: str
    doc_url: str
    doc_provenance: str
    expected_behavior: str
    required_validation_tests: List[str]
    known_limitations: str
    confidence: RuleConfidence = RuleConfidence.CONFIRMED
    is_deterministic: bool = True
    openrewrite_recipe: Optional[str] = None
    replacement_mapping: Dict[str, str] = field(default_factory=dict)

# Versioned registry definitions
MIGRATION_RULES: Dict[str, MigrationRule] = {
    "RULE-JAKARTA-EE-PERSISTENCE": MigrationRule(
        rule_id="RULE-JAKARTA-EE-PERSISTENCE",
        title="Migrate javax.persistence to jakarta.persistence",
        category=RuleCategory.NAMESPACE,
        source_version_constraint="Spring Boot 2.x (Java EE 8)",
        target_version_constraint="Spring Boot 3.x (Jakarta EE 9/10)",
        description="Spring Boot 3.0 has migrated from Java EE 8 APIs to Jakarta EE 9/10 APIs, requiring changing package javax.persistence to jakarta.persistence.",
        affected_pattern="import javax.persistence.",
        doc_url="https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-3.0-Migration-Guide#jakarta-ee",
        doc_provenance="Official Spring Boot 3.0 Migration Guide (Wiki)",
        expected_behavior="All javax.persistence package references and annotations are rewritten to jakarta.persistence equivalent classes.",
        required_validation_tests=["CustomerTest", "EntityMappingCompilationCheck"],
        known_limitations="Does not cover non-standard vendor-specific persistence extensions without Jakarta equivalents.",
        confidence=RuleConfidence.CONFIRMED,
        is_deterministic=True,
        openrewrite_recipe="org.openrewrite.java.migrate.jakarta.JavaxPersistenceToJakartaPersistence",
        replacement_mapping={
            "import javax.persistence.": "import jakarta.persistence."
        }
    ),
    "RULE-JAKARTA-EE-SERVLET": MigrationRule(
        rule_id="RULE-JAKARTA-EE-SERVLET",
        title="Migrate javax.servlet to jakarta.servlet",
        category=RuleCategory.NAMESPACE,
        source_version_constraint="Spring Boot 2.x",
        target_version_constraint="Spring Boot 3.x",
        description="Servlet spec upgrade from Servlet 4.0 (javax.servlet) to Servlet 5.0/6.0 (jakarta.servlet).",
        affected_pattern="import javax.servlet.",
        doc_url="https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-3.0-Migration-Guide#jakarta-ee",
        doc_provenance="Official Spring Boot 3.0 Migration Guide (Wiki)",
        expected_behavior="All javax.servlet imports and type references replaced by jakarta.servlet.",
        required_validation_tests=["ServletEndpointTest"],
        known_limitations="Custom filters and wrappers must also ensure binary compatibility with Servlet 6.0 methods.",
        confidence=RuleConfidence.CONFIRMED,
        is_deterministic=True,
        openrewrite_recipe="org.openrewrite.java.migrate.jakarta.JavaxServletToJakartaServlet",
        replacement_mapping={
            "import javax.servlet.": "import jakarta.servlet."
        }
    ),
    "RULE-JAKARTA-EE-VALIDATION": MigrationRule(
        rule_id="RULE-JAKARTA-EE-VALIDATION",
        title="Migrate javax.validation to jakarta.validation",
        category=RuleCategory.NAMESPACE,
        source_version_constraint="Spring Boot 2.x",
        target_version_constraint="Spring Boot 3.x",
        description="Bean Validation migration from javax.validation to jakarta.validation.",
        affected_pattern="import javax.validation.",
        doc_url="https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-3.0-Migration-Guide#jakarta-ee",
        doc_provenance="Official Spring Boot 3.0 Migration Guide (Wiki)",
        expected_behavior="Replace javax.validation annotations (@NotNull, @Size, @Valid, etc.) with jakarta.validation equivalents.",
        required_validation_tests=["ValidationModelTest"],
        known_limitations="Hibernate Validator custom validator interfaces must target jakarta.validation.ConstraintValidator.",
        confidence=RuleConfidence.CONFIRMED,
        is_deterministic=True,
        openrewrite_recipe="org.openrewrite.java.migrate.jakarta.JavaxValidationToJakartaValidation",
        replacement_mapping={
            "import javax.validation.": "import jakarta.validation."
        }
    ),
    "RULE-JAKARTA-EE-ANNOTATION": MigrationRule(
        rule_id="RULE-JAKARTA-EE-ANNOTATION",
        title="Migrate javax.annotation to jakarta.annotation",
        category=RuleCategory.NAMESPACE,
        source_version_constraint="Spring Boot 2.x",
        target_version_constraint="Spring Boot 3.x",
        description="Lifecycle annotations @PostConstruct, @PreDestroy, @Resource migrated from javax.annotation to jakarta.annotation.",
        affected_pattern="import javax.annotation.",
        doc_url="https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-3.0-Migration-Guide#jakarta-ee",
        doc_provenance="Official Spring Boot 3.0 Migration Guide (Wiki)",
        expected_behavior="Lifecycle annotations rewritten to jakarta.annotation.",
        required_validation_tests=["LifecycleInitTest"],
        known_limitations="None for standard @PostConstruct and @PreDestroy.",
        confidence=RuleConfidence.CONFIRMED,
        is_deterministic=True,
        openrewrite_recipe="org.openrewrite.java.migrate.jakarta.JavaxAnnotationToJakartaAnnotation",
        replacement_mapping={
            "import javax.annotation.": "import jakarta.annotation."
        }
    ),
    "RULE-POM-DEPENDENCIES-SB3": MigrationRule(
        rule_id="RULE-POM-DEPENDENCIES-SB3",
        title="Upgrade Maven Spring Boot Parent & Jakarta Dependencies",
        category=RuleCategory.DEPENDENCY,
        source_version_constraint="Spring Boot 2.x (2.7.x)",
        target_version_constraint="Spring Boot 3.x (3.2.x)",
        description="Updates Maven pom.xml dependencies and spring.boot.version property to 3.2.0, updating javax coordinate artifacts to jakarta equivalents.",
        affected_pattern="<spring.boot.version>2. | javax.persistence-api | javax.servlet-api | javax.annotation-api | validation-api",
        doc_url="https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-3.0-Migration-Guide#upgrading-from-spring-boot-2x",
        doc_provenance="Spring Boot Release Notes & Migration Guides",
        expected_behavior="Upgrades declared Spring Boot version to 3.2.0 and changes Maven GAV coordinates for Jakarta EE specs.",
        required_validation_tests=["MavenCompileCheck", "MavenDependencyConvergenceCheck"],
        known_limitations="Requires target JDK 17 or higher.",
        confidence=RuleConfidence.CONFIRMED,
        is_deterministic=True,
        openrewrite_recipe="org.openrewrite.java.spring.boot3.UpgradeSpringBoot_3_0",
        replacement_mapping={
            "<spring.boot.version>2.7.18</spring.boot.version>": "<spring.boot.version>3.2.0</spring.boot.version>",
            "<groupId>javax.persistence</groupId>\n            <artifactId>javax.persistence-api</artifactId>\n            <version>2.2</version>": "<groupId>jakarta.persistence</groupId>\n            <artifactId>jakarta.persistence-api</artifactId>\n            <version>3.1.0</version>",
            "<groupId>javax.servlet</groupId>\n            <artifactId>javax.servlet-api</artifactId>\n            <version>4.0.1</version>": "<groupId>jakarta.servlet</groupId>\n            <artifactId>jakarta.servlet-api</artifactId>\n            <version>6.0.0</version>",
            "<groupId>javax.validation</groupId>\n            <artifactId>validation-api</artifactId>\n            <version>2.0.1.Final</version>": "<groupId>jakarta.validation</groupId>\n            <artifactId>jakarta.validation-api</artifactId>\n            <version>3.0.2</version>",
            "<groupId>javax.annotation</groupId>\n            <artifactId>javax.annotation-api</artifactId>\n            <version>1.3.2</version>": "<groupId>jakarta.annotation</groupId>\n            <artifactId>jakarta.annotation-api</artifactId>\n            <version>2.1.1</version>",
        }
    ),
    "RULE-CONFIG-REDIS-PREFIX": MigrationRule(
        rule_id="RULE-CONFIG-REDIS-PREFIX",
        title="Migrate spring.redis.* Configuration Prefix to spring.data.redis.*",
        category=RuleCategory.CONFIGURATION,
        source_version_constraint="Spring Boot 2.x",
        target_version_constraint="Spring Boot 3.x",
        description="In Spring Boot 3.0, redis properties were moved under the spring.data.redis prefix.",
        affected_pattern="spring.redis.",
        doc_url="https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-3.0-Migration-Guide#redis-properties",
        doc_provenance="Official Spring Boot 3.0 Configuration Changelog",
        expected_behavior="Property keys prefixed with spring.redis.* become spring.data.redis.*.",
        required_validation_tests=["ApplicationPropertiesLoadTest"],
        known_limitations="Does not automatically migrate custom third-party Redis configuration beans.",
        confidence=RuleConfidence.CONFIRMED,
        is_deterministic=True,
        openrewrite_recipe="org.openrewrite.spring.boot3.SpringBootProperties_3_0",
        replacement_mapping={
            "spring.redis.": "spring.data.redis."
        }
    ),
    "RULE-CONFIG-MAX-HTTP-HEADER": MigrationRule(
        rule_id="RULE-CONFIG-MAX-HTTP-HEADER",
        title="Migrate server.max-http-header-size to server.max-http-request-header-size",
        category=RuleCategory.CONFIGURATION,
        source_version_constraint="Spring Boot 2.x",
        target_version_constraint="Spring Boot 3.x",
        description="The property server.max-http-header-size was renamed in Spring Boot 3 to server.max-http-request-header-size.",
        affected_pattern="server.max-http-header-size",
        doc_url="https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-3.0-Migration-Guide#server-properties",
        doc_provenance="Official Spring Boot 3.0 Server Property Reference",
        expected_behavior="Replaces server.max-http-header-size with server.max-http-request-header-size.",
        required_validation_tests=["ServerConfigValidationTest"],
        known_limitations="None.",
        confidence=RuleConfidence.CONFIRMED,
        is_deterministic=True,
        openrewrite_recipe="org.openrewrite.spring.boot3.SpringBootProperties_3_0",
        replacement_mapping={
            "server.max-http-header-size": "server.max-http-request-header-size"
        }
    ),
    "RULE-SPRING-SECURITY-6-FILTER": MigrationRule(
        rule_id="RULE-SPRING-SECURITY-6-FILTER",
        title="Migrate WebSecurityConfigurerAdapter to SecurityFilterChain Bean",
        category=RuleCategory.SECURITY,
        source_version_constraint="Spring Security 5.x / Boot 2.x",
        target_version_constraint="Spring Security 6.x / Boot 3.x",
        description="WebSecurityConfigurerAdapter is removed in Spring Security 6.x. Replace with a SecurityFilterChain @Bean and migrate authorizeRequests() to authorizeHttpRequests().",
        affected_pattern="WebSecurityConfigurerAdapter | authorizeRequests()",
        doc_url="https://docs.spring.io/spring-security/reference/5.8/migration/index.html",
        doc_provenance="Spring Security 5.8 to 6.0 Migration Guide",
        expected_behavior="Deprecates class extension and converts security DSL to lambda-based SecurityFilterChain bean.",
        required_validation_tests=["SecurityFilterChainIntegrationTest"],
        known_limitations="Complex custom AuthenticationProvider hierarchies may require additional lambda configuration.",
        confidence=RuleConfidence.CONFIRMED,
        is_deterministic=False,  # Contextual: complex architectural refactoring
        openrewrite_recipe="org.openrewrite.java.spring.security6.UpgradeSpringSecurity_6_0",
        replacement_mapping={
            "authorizeRequests()": "authorizeHttpRequests()",
            "antMatchers(": "requestMatchers("
        }
    )
}

def get_rule_by_id(rule_id: str) -> Optional[MigrationRule]:
    return MIGRATION_RULES.get(rule_id)

def list_all_rules() -> List[MigrationRule]:
    return list(MIGRATION_RULES.values())
