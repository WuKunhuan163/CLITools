---
name: pytorch-deep-learning
description: PyTorch deep learning development patterns. Use when working with pytorch deep learning concepts or setting up related projects.
---

# PyTorch Deep Learning

## Core Principles

- **Dynamic Computation Graph**: Build graph on-the-fly; debug with standard Python
- **Module System**: Subclass `nn.Module` for all model components
- **DataLoader**: Use for batching, shuffling, and parallel data loading
- **Device Management**: Explicitly move tensors and models to GPU

## Key Patterns

### Model Definition
```python
class ConvNet(nn.Module):
    def __init__(self, num_classes=10):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 64, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(64, 128, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
        )
        self.classifier = nn.Linear(128 * 8 * 8, num_classes)

    def forward(self, x):
        x = self.features(x)
        x = x.view(x.size(0), -1)
        return self.classifier(x)
```

### Training Loop
```python
model.train()
for epoch in range(num_epochs):
    for batch_x, batch_y in dataloader:
        batch_x, batch_y = batch_x.to(device), batch_y.to(device)
        optimizer.zero_grad()
        output = model(batch_x)
        loss = criterion(output, batch_y)
        loss.backward()
        optimizer.step()
```

### Checkpointing
```python
torch.save({'model': model.state_dict(), 'optimizer': optimizer.state_dict(), 'epoch': epoch}, 'checkpoint.pt')
```

## Anti-Patterns
- Not calling `model.eval()` and `torch.no_grad()` during inference
- Accumulating gradients across batches (forgetting `zero_grad()`)
- Loading entire dataset into memory (use DataLoader with workers)
