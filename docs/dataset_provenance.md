# Dataset Provenance & Data Splits

## 1. Overview
The fine-tuning dataset for PatchPilot comprises paired source code and migration targets mapping Spring Boot 2.7.x implementations to Spring Boot 3.2.x specifications.

## 2. Provenance Sources
- **Official Spring Boot 3.0 Migration Guide**: https://github.com/spring-projects/spring-boot/wiki/Spring-Boot-3.0-Migration-Guide
- **Jakarta EE 9/10 Specification Transition Reference**: https://jakarta.ee/specifications/
- **Spring Security 6.0 Migration Guides**: https://docs.spring.io/spring-security/reference/5.8/migration/index.html
- **OpenRewrite Recipe Specifications**: Apache-2.0 licensed migration patterns from `rewrite-spring` and `rewrite-migrate-java`.

## 3. Dataset Schemas & Schema Validation
Each example is stored with the following schema in `datasets/processed/{train,validation,test}.json`:
```json
{
  "example_id": "string",
  "repository_name": "string",
  "file_path": "string",
  "source_framework_version": "string",
  "target_framework_version": "string",
  "migration_rule_id": "string",
  "documentation_context": "string",
  "original_code": "string",
  "target_code": "string",
  "validation_expectations": "string",
  "license": "string",
  "provenance": "string"
}
```

## 4. Deduplication & Partitioning Strategy
1. **Cryptographic Deduplication**: SHA-256 hashes of concatenated `original_code` and `target_code` are checked to prune duplicate examples.
2. **Repository-Grouped Splits**: Partitioning into `train`, `validation`, and `test` splits is grouped strictly by `repository_name`. Test repositories are never observed during training or validation, ensuring zero data leakage.
