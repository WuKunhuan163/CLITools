---
name: fine-tuning-llms
description: LLM fine-tuning techniques and best practices. Use when working with fine tuning llms concepts or setting up related projects.
---

# Fine-Tuning LLMs

## Approaches

### Full Fine-Tuning
Train all model parameters. Requires significant compute.

### LoRA (Low-Rank Adaptation)
```python
from peft import LoraConfig, get_peft_model

lora_config = LoraConfig(
    r=8, lora_alpha=32, target_modules=["q_proj", "v_proj"],
    lora_dropout=0.05, task_type="CAUSAL_LM"
)
model = get_peft_model(base_model, lora_config)
# Only ~0.1% of parameters are trainable
```

### QLoRA (Quantized LoRA)
4-bit quantization + LoRA for consumer GPU fine-tuning.

## Data Preparation

### Instruction Format
```json
{"instruction": "Summarize this article", "input": "Long article text...", "output": "Brief summary..."}
```

### Chat Format
```json
{"messages": [
  {"role": "system", "content": "You are a helpful assistant."},
  {"role": "user", "content": "What is Python?"},
  {"role": "assistant", "content": "Python is a programming language..."}
]}
```

## Best Practices
- Start with high-quality, diverse training data (100-1000 examples minimum)
- Use validation set to detect overfitting
- Learning rate: 1e-5 to 5e-5 for full fine-tuning; 1e-4 to 3e-4 for LoRA
- Evaluate with task-specific metrics, not just loss

## Anti-Patterns
- Fine-tuning when prompt engineering suffices
- Training on noisy/low-quality data
- Not evaluating on held-out test set
- Overfitting to small dataset (watch validation loss)
