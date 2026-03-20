---
name: ml-experiment-tracking
description: ML experiment tracking and reproducibility. Use when working with ml experiment tracking concepts or setting up related projects.
---

# ML Experiment Tracking

## Core Principles

- **Track Everything**: Parameters, metrics, artifacts, code version
- **Reproducibility**: Same inputs should produce same outputs
- **Compare Experiments**: Easy comparison of different runs
- **Model Registry**: Version and stage models (staging, production)

## MLflow Example
```python
import mlflow

mlflow.set_experiment("text-classification")
with mlflow.start_run():
    mlflow.log_params({"lr": 0.001, "epochs": 10, "model": "bert-base"})
    for epoch in range(10):
        train_loss = train(model)
        val_acc = evaluate(model)
        mlflow.log_metrics({"train_loss": train_loss, "val_acc": val_acc}, step=epoch)
    mlflow.pytorch.log_model(model, "model")
```

## Weights & Biases Example
```python
import wandb
wandb.init(project="my-project", config={"lr": 0.001})
for epoch in range(10):
    wandb.log({"loss": loss, "accuracy": acc})
wandb.finish()
```

## Best Practices
- Version datasets alongside model code
- Log environment info (Python version, package versions)
- Use config files (YAML/JSON) for hyperparameters
- Tag experiments with meaningful labels
- Set random seeds for reproducibility

## Experiment Comparison Checklist
- Same dataset split (train/val/test)
- Same evaluation metrics
- Same preprocessing pipeline
- Same hardware (or account for differences)
