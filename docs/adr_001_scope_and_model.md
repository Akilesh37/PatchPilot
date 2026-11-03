# ADR 001: Migration Scope and Code Model Selection

## Status
Accepted

## Context
Migrating Java repositories across major framework revisions (Spring Boot 2.x to 3.x) introduces both syntactic namespace refactorings (Jakarta EE transition) and semantic API contract breaks (Spring Security 6, property hierarchy relocations). We evaluated candidate open-weight models and baseline architectures to determine the optimal balance of parameter efficiency, inference latency, hardware reproducibility, and code understanding.

## Decision
1. **Target Baseline**: Constrain initial target scope to Spring Boot 2.7.x to Spring Boot 3.2.0, focusing on Jakarta EE 9/10, standard Maven builds, and Spring Security 6 basics.
2. **Model Choice**: Selected `Qwen/Qwen2.5-Coder-3B-Instruct` as candidate code LLM due to:
   - Strong code synthesis benchmarks relative to model parameter footprint.
   - Compatibility with 4-bit/8-bit QLoRA on single consumer/cloud GPUs (A10G / 24GB).
   - Fast inference latency compared to 7B/14B models.
   - Permissive open weights license.
3. **PEFT with LoRA**: Use Parameter-Efficient Fine-Tuning ($r=16, \alpha=32$) targeting attention projections (`q_proj`, `v_proj`) and MLP projections, enabling reproducible lightweight adapter weights.
4. **Architectural Grounding**: Complement model generation with version-aware BM25 documentation retrieval and execution-based verification with a bounded self-repair loop ($N \le 2$).

## Consequences
- Prevents unbounded hallucination of deprecated methods.
- Retains fast local smoke-testing capability on Apple Silicon MPS and CPU.
- Preserves full auditability with unified diff previews and review controls.
