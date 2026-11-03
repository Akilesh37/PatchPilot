"""
Reproducible Parameter-Efficient Fine-Tuning (PEFT) pipeline with LoRA and QLoRA.
Enforces strict distinction between unquantized LoRA and 4-bit QLoRA.
Transparently logs model parameters, hardware architecture, execution tier,
and computes training and validation loss metrics with zero data leakage.
"""
import argparse
import datetime
import json
import os
import sys
from typing import Optional
import torch
from peft import LoraConfig, get_peft_model, TaskType
from transformers import AutoModelForCausalLM, AutoTokenizer, TrainingArguments, Trainer

def format_instruction_prompt(item: dict) -> str:
    return f"""<|im_start|>system
You are PatchPilot, an expert software migration engineer.
Evidence Context:
{item.get('documentation_context', '')}
Task: Migrate the code from {item.get('source_framework_version', 'Spring Boot 2.x')} to {item.get('target_framework_version', 'Spring Boot 3.x')}.<|im_end|>
<|im_start|>user
File: {item.get('file_path', '')}
```java
{item.get('original_code', '')}
```<|im_end|>
<|im_start|>assistant
```java
{item.get('target_code', '')}
```<|im_end|>"""

class SftDataset(torch.utils.data.Dataset):
    def __init__(self, encodings):
        self.encodings = encodings

    def __getitem__(self, idx):
        return {key: val[idx] for key, val in self.encodings.items()}

    def __len__(self):
        return len(self.encodings.input_ids)

def run_training(
    model_name: str,
    data_path: str,
    output_dir: str,
    val_data_path: Optional[str] = "datasets/processed/validation.json",
    mode: str = "lora",
    epochs: int = 1,
    lora_r: int = 16,
    lora_alpha: int = 32,
    lr: float = 2e-4,
    smoke_test: bool = False
):
    print("=" * 60)
    print("PatchPilot Fine-Tuning Pipeline (PEFT)")
    print(f"Requested Mode: {mode.upper()}")
    print(f"Model ID: {model_name}")
    print(f"Output Directory: {output_dir}")
    print("=" * 60)

    device = "mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Hardware Detected: {device.upper()}")

    # Enforce strict validation: QLoRA requires CUDA + bitsandbytes
    if mode.lower() == "qlora":
        if device != "cuda":
            print("[ERROR] QLoRA requires 4-bit NormalFloat (NF4) quantization via bitsandbytes, which requires a CUDA GPU.")
            print(f"Current hardware is '{device}'. On Apple Silicon MPS or CPU, unquantized LoRA (16-bit) must be used.")
            raise RuntimeError(f"Cannot run QLoRA on {device}. Use --mode lora for Apple Silicon MPS or CPU.")

    # Load dataset
    if not os.path.exists(data_path):
        from ml.data.dataset_builder import DatasetBuilder
        builder = DatasetBuilder()
        builder.build_and_split()

    with open(data_path, "r", encoding="utf-8") as f:
        raw_items = json.load(f)

    if smoke_test:
        raw_items = raw_items[:2]

    texts = [format_instruction_prompt(item) for item in raw_items]

    # Tokenizer setup
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    encodings = tokenizer(
        texts,
        truncation=True,
        max_length=512 if smoke_test else 2048,
        padding="max_length",
        return_tensors="pt"
    )
    encodings["labels"] = encodings["input_ids"].clone()
    train_dataset = SftDataset(encodings)

    # Optional validation dataset
    val_dataset = None
    if val_data_path and os.path.exists(val_data_path):
        with open(val_data_path, "r", encoding="utf-8") as f:
            val_items = json.load(f)
        if smoke_test:
            val_items = val_items[:1]
        val_texts = [format_instruction_prompt(item) for item in val_items]
        val_encodings = tokenizer(
            val_texts,
            truncation=True,
            max_length=512 if smoke_test else 2048,
            padding="max_length",
            return_tensors="pt"
        )
        val_encodings["labels"] = val_encodings["input_ids"].clone()
        val_dataset = SftDataset(val_encodings)

    # Base Model Loading
    quantization_config = None
    if mode.lower() == "qlora":
        from transformers import BitsAndBytesConfig
        quantization_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True
        )
        base_model = AutoModelForCausalLM.from_pretrained(
            model_name,
            quantization_config=quantization_config,
            device_map="auto"
        )
    else:
        torch_dtype = torch.float16 if device in ["cuda", "mps"] else torch.float32
        base_model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch_dtype
        )

    total_base_params = sum(p.numel() for p in base_model.parameters())
    print(f"Base Model Total Parameters: {total_base_params:,}")

    # Configure LoRA targets
    if "gpt2" in model_name.lower():
        target_modules = ["c_attn"]
    else:
        target_modules = ["q_proj", "v_proj", "k_proj", "o_proj"]

    peft_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=lora_r,
        lora_alpha=lora_alpha,
        lora_dropout=0.05,
        target_modules=target_modules
    )
    model = get_peft_model(base_model, peft_config)

    trainable_params, all_params = model.get_nb_trainable_parameters()
    trainable_pct = (trainable_params / all_params) * 100
    print(f"Trainable Parameters: {trainable_params:,} / {all_params:,} ({trainable_pct:.4f}%)")

    os.makedirs(output_dir, exist_ok=True)

    eval_strategy = "epoch" if val_dataset else "no"
    training_args = TrainingArguments(
        output_dir=output_dir,
        num_train_epochs=epochs,
        per_device_train_batch_size=1,
        learning_rate=lr,
        logging_steps=1,
        save_strategy="no",
        eval_strategy=eval_strategy,
        use_cpu=(device == "cpu"),
        report_to="none"
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=val_dataset
    )

    train_result = trainer.train()
    print("Fine-tuning completed successfully!")
    print(f"Final Training Loss: {train_result.training_loss:.4f}")

    val_loss = None
    if val_dataset:
        eval_metrics = trainer.evaluate()
        val_loss = eval_metrics.get("eval_loss")
        print(f"Evaluation Loss: {val_loss}")

    # Save adapter
    adapter_path = os.path.join(output_dir, "adapter")
    model.save_pretrained(adapter_path)
    tokenizer.save_pretrained(adapter_path)

    summary = {
        "model_id": model_name,
        "mode": mode.lower(),
        "total_parameters": all_params,
        "trainable_parameters": trainable_params,
        "trainable_percentage": round(trainable_pct, 4),
        "device": device,
        "epochs": epochs,
        "lora_rank": lora_r,
        "lora_alpha": lora_alpha,
        "learning_rate": lr,
        "final_loss": round(train_result.training_loss, 4),
        "validation_loss": round(val_loss, 4) if val_loss is not None else None,
        "is_smoke_test": smoke_test,
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
    }

    with open(os.path.join(output_dir, "training_summary.json"), "w") as f:
        json.dump(summary, f, indent=2)

    return summary

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PatchPilot LoRA/QLoRA Training")
    parser.add_argument("--mode", type=str, default="lora", choices=["lora", "qlora"], help="Fine-tuning mode: lora (16-bit) or qlora (4-bit NF4)")
    parser.add_argument("--model", type=str, default="hf-internal-testing/tiny-random-gpt2", help="Base model identifier")
    parser.add_argument("--data", type=str, default="datasets/processed/train.json", help="Path to training dataset")
    parser.add_argument("--val-data", type=str, default="datasets/processed/validation.json", help="Path to validation dataset")
    parser.add_argument("--output", type=str, default="checkpoints/smoke_test_lora", help="Output directory")
    parser.add_argument("--epochs", type=int, default=1, help="Number of epochs")
    parser.add_argument("--smoke-test", action="store_true", help="Run fast smoke-test mode")
    args = parser.parse_args()

    run_training(
        model_name=args.model,
        data_path=args.data,
        val_data_path=args.val_data,
        output_dir=args.output,
        mode=args.mode,
        epochs=args.epochs,
        smoke_test=args.smoke_test
    )
