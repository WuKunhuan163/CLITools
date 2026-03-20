---
name: nlp-text-processing
description: NLP and text processing techniques. Use when working with nlp text processing concepts or setting up related projects.
---

# NLP & Text Processing

## Core Techniques

### Text Preprocessing
```python
import re

def preprocess(text: str) -> str:
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)       # remove punctuation
    text = re.sub(r'\s+', ' ', text).strip()   # normalize whitespace
    return text
```

### Tokenization (Hugging Face)
```python
from transformers import AutoTokenizer
tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")
tokens = tokenizer("Hello, world!", return_tensors="pt")
```

### Sentiment Analysis
```python
from transformers import pipeline
classifier = pipeline("sentiment-analysis")
result = classifier("This product is fantastic!")
# [{'label': 'POSITIVE', 'score': 0.9998}]
```

### Named Entity Recognition
```python
ner = pipeline("ner", grouped_entities=True)
entities = ner("Apple Inc. was founded by Steve Jobs in Cupertino.")
# [{'entity_group': 'ORG', 'word': 'Apple Inc.'}, ...]
```

## Text Similarity
```python
from sentence_transformers import SentenceTransformer, util
model = SentenceTransformer('all-MiniLM-L6-v2')
embeddings = model.encode(["Hello world", "Hi there"])
similarity = util.cos_sim(embeddings[0], embeddings[1])
```

## Common Tasks
- **Classification**: Spam detection, sentiment, topic categorization
- **NER**: Extract people, places, organizations
- **Summarization**: Condense long text
- **Translation**: Language-to-language conversion
- **Question Answering**: Extract answers from context
