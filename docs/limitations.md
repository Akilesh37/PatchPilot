# Limitations & Failure Taxonomy

## 1. Supported Scope & Boundaries
PatchPilot explicitly supports migrations from **Spring Boot 2.7.x** baseline to **Spring Boot 3.2.x** target for standard Maven projects.
The system does not claim universal support for every arbitrary legacy architecture.

Specifically supported migration categories:
- Jakarta EE 9/10 namespace migration (`javax.persistence.*`, `javax.servlet.*`, `javax.validation.*`, `javax.annotation.*`).
- Maven coordinate updates (upgrading parent to Spring Boot 3.2.0, rewriting javax dependency coordinates to Jakarta equivalents).
- Standard Spring Boot 3 configuration property renames (`spring.redis.*` -> `spring.data.redis.*`, `server.max-http-header-size` -> `server.max-http-request-header-size`).
- Spring Security 5 to 6 DSL migrations (`authorizeRequests()` to `authorizeHttpRequests()`).

## 2. Known Limitations
1. **Third-Party Bytecode Incompatibilities**: Third-party libraries that still depend on `javax.servlet` at runtime without Jakarta-compatible releases will fail during integration tests.
2. **Complex Gradle Multi-Module Builds**: While single-module Gradle builds are parsed, complex composite builds require Maven or standard directory layout.
3. **Complex Custom Security Filters**: Highly custom authentication provider hierarchies extending internal Spring Security classes may require manual intervention.
4. **Target JDK Requirement**: Spring Boot 3 strictly requires Java 17 or higher. Projects with source/target Java 8/11 must upgrade their toolchain.

## 3. Failure Taxonomy
When automated migrations encounter issues, failures are categorized into:
- `MISSED_CALL_SITES`: Patterns appearing inside generated source or reflection that AST parser did not detect.
- `INCORRECT_API_SUBSTITUTIONS`: Deprecated methods replaced with invalid signatures.
- `INCOMPLETE_DEPENDENCY_UPDATES`: Transitive dependencies with conflicting javax/jakarta requirements.
- `COMPILATION_FAILURES`: javac errors (e.g. missing symbols).
- `TEST_REGRESSIONS`: Functional assertions failing post-migration.
- `UNSUPPORTED_ASSUMPTIONS`: Custom third-party proprietary frameworks lacking open migration recipes.
