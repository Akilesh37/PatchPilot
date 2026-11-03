# Model Fine-Tuning Guide (LoRA vs QLoRA)

## 1. Architectural Distinction: LoRA vs QLoRA

It is critical to distinguish between **LoRA** and **QLoRA**:

| Feature | Standard LoRA | QLoRA |
|---|---|---|
| **Base Model Precision** | 16-bit (FP16 or BF16) | 4-bit NormalFloat (NF4) |
| **Adapter Rank ($r$)** | Low-rank matrices ($W = W_0 + B \times A$) | Low-rank matrices with double quantization |
| **Hardware Requirement** | Apple Silicon MPS, Linux CUDA, or CPU | Requires NVIDIA CUDA GPU + `bitsandbytes` |
| **VRAM for 3B Model** | ~7.2 GB VRAM | ~3.8 GB VRAM |
| **Current Local Support** | Native in PyTorch + PEFT on macOS MPS | Blocked on macOS (bitsandbytes requires CUDA) |

> **Important**: The local training runs performed on Apple Silicon MPS utilize **16-bit unquantized LoRA**, not QLoRA. Calling an unquantized LoRA training run "QLoRA" is technically inaccurate.

---

## 2. Model Architecture & Parameter Verification

- **Target Production Model**: `Qwen/Qwen2.5-Coder-3B-Instruct`
  - Total Base Parameters: **3,086,180,352** (~3.09 Billion parameters)
  - Vocabulary Size: 151,646 tokens
  - Context Window: 32,768 tokens
  - Target Projections: `q_proj`, `k_proj`, `v_proj`, `o_proj`, `gate_proj`, `up_proj`, `down_proj`
  - Trainable Parameters with LoRA ($r=16$): ~18,432,000 (~0.60% of total)

- **Local Pipeline Smoke Test**: `hf-internal-testing/tiny-random-gpt2`
  - Total Base Parameters: **111,968**
  - Trainable Parameters ($r=16$): **10,240** (8.38% of total)
  - Purpose: Validates tokenization, forward pass, gradient calculation, loss convergence, and PEFT adapter serialization on Apple Silicon MPS without multi-gigabyte weight downloads.
  - Final Loss: 6.8863

---

## 3. Training Execution Commands

### Local Smoke-Test (Apple Silicon MPS / CPU)
```bash
.venv/bin/python3 ml/training/train_lora.py \
  --mode lora \
  --smoke-test \
  --output checkpoints/smoke_test_lora
```

### Full-Scale LoRA on Apple Silicon (Requires ~8GB RAM)
```bash
.venv/bin/python3 ml/training/train_lora.py \
  --mode lora \
  --model "Qwen/Qwen2.5-Coder-3B-Instruct" \
  --data "datasets/processed/train.json" \
  --output "checkpoints/qwen_coder_3b_lora" \
  --epochs 3
```

### Full-Scale QLoRA on Linux NVIDIA GPU (CUDA + bitsandbytes)
```bash
python3 ml/training/train_lora.py \
  --mode qlora \
  --model "Qwen/Qwen2.5-Coder-3B-Instruct" \
  --data "datasets/processed/train.json" \
  --output "checkpoints/qwen_coder_3b_qlora" \
  --epochs 3
```
If `--mode qlora` is invoked without CUDA, the script automatically halts with an informative error explaining hardware incompatibility.
