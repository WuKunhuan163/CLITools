---
name: ml-deployment
description: Machine learning model deployment patterns. Use when working with ml deployment concepts or setting up related projects.
---

# ML Model Deployment

## Deployment Patterns

### Batch Inference
- Process large datasets on schedule (daily, hourly)
- Use Spark, Airflow, or cloud batch services
- Good for: recommendations, reports, data pipelines

### Real-Time Inference (API)
```python
# FastAPI model serving
@app.post("/predict")
async def predict(input: PredictRequest):
    features = preprocess(input)
    prediction = model.predict(features)
    return {"prediction": prediction.tolist()}
```

### Model Registry
```python
import mlflow
mlflow.pytorch.log_model(model, "model")
mlflow.register_model("runs:/<run-id>/model", "production-model")
```

## Model Serving Options
1. **Custom API** (FastAPI/Flask): Full control, custom preprocessing
2. **TensorFlow Serving**: Optimized for TF models, gRPC/REST
3. **Triton Inference Server**: Multi-framework, GPU optimized
4. **SageMaker/Vertex AI**: Managed, auto-scaling

## Best Practices
- Version models with their preprocessing code
- A/B test new models before full rollout
- Monitor model drift (data distribution changes)
- Shadow mode: run new model alongside old before switching
- Log predictions for debugging and retraining

## Anti-Patterns
- Training and serving code are separate (use same preprocessing)
- No model versioning or rollback capability
- Not monitoring prediction distribution over time
