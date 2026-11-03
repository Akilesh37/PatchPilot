# Research Methodology & Experimental Design

## 1. Research Question
Can parameter-efficient fine-tuning (PEFT/QLoRA), combined with version-aware documentation retrieval and execution-based verification, improve the success rate of repository-level software migrations compared with rule-based tools and prompting-based LLM systems?

## 2. Experimental Systems Under Evaluation
We evaluate six distinct systems across the exact same held-out benchmark tasks:

1. **System A (Deterministic OpenRewrite Baseline)**: Standard rule/recipe-based AST replacements for known migration coordinates.
2. **System B (Base Code LLM Zero-Shot)**: Base code instruction model prompted with original code and migration goal without documentation or examples.
3. **System C (Base Code LLM Few-Shot)**: Base code model provided with in-context examples of valid migrations.
4. **System D (Base Code LLM + Documentation RAG)**: Base code model conditioned on BM25-retrieved sections of the official Spring Boot 3 migration documentation.
5. **System E (QLoRA Fine-Tuned LLM)**: Model fine-tuned on curated Spring Boot 2.x to 3.x pairs with LoRA adapters ($r=16, \alpha=32$).
6. **System F (Full PatchPilot)**: QLoRA fine-tuned model + version-aware documentation retrieval + isolated verification worker + bounded diagnostic self-repair loop ($N \le 2$).

## 3. Data Isolation & Leakage Prevention
To ensure rigorous evaluation:
- All training and test splits are partitioned strictly by **repository name** rather than by file or snippet.
- No file or call site from a repository in the test set appears in the training or validation splits.
- Exact hashes of snippets are deduplicated to avoid memorization.

## 4. Evaluation Metrics
- **End-to-End Success Rate**: Proportion of repository migrations where all changes compile cleanly, pass all unit tests, and introduce zero regressions.
- **Build Success Rate**: Proportion of migrated repositories compiling without javac errors (`mvn compile`).
- **Unit Test Success Rate**: Proportion of migrated repositories where all JUnit 5 tests succeed (`mvn test`).
- **Localization Precision, Recall, and F1**: Accuracy in identifying affected call sites.
- **Unnecessary Edit Rate**: Frequency of modifications to unaffected methods or dependencies.
- **Inference Latency**: Mean execution time per file transformation.
