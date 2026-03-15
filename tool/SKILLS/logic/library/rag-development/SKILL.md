---
name: rag-development
description: Retrieval-Augmented Generation (RAG) architecture. Use when working with rag development concepts or setting up related projects.
---

# RAG Development

## Core Architecture

```
Query -> Embedding -> Vector Search -> Context Retrieval -> LLM Generation
```

## Components

### 1. Document Processing
```python
# Chunking strategy
chunks = []
for doc in documents:
    text_chunks = split_text(doc.content, chunk_size=512, overlap=50)
    for chunk in text_chunks:
        chunks.append({"text": chunk, "metadata": doc.metadata})
```

### 2. Embedding
```python
from openai import OpenAI
client = OpenAI()

def embed(texts: list[str]) -> list[list[float]]:
    response = client.embeddings.create(model="text-embedding-3-small", input=texts)
    return [item.embedding for item in response.data]
```

### 3. Vector Store (Retrieval)
```python
# Using chromadb
collection.query(query_embeddings=[query_embedding], n_results=5)
```

### 4. Generation with Context
```python
context = "\n".join([doc["text"] for doc in retrieved_docs])
response = client.chat.completions.create(
    model="gpt-4",
    messages=[
        {"role": "system", "content": f"Answer based on context:\n{context}"},
        {"role": "user", "content": query}
    ]
)
```

## Optimization Techniques
- **Hybrid Search**: Combine vector search with BM25 keyword search
- **Re-ranking**: Use cross-encoder to re-rank retrieved documents
- **Chunk Overlap**: Prevent context loss at chunk boundaries
- **Metadata Filtering**: Pre-filter by date, source, category

## Anti-Patterns
- Chunks too large (noise) or too small (lost context)
- Not including metadata in retrieval
- Stuffing too much context (exceeding model window)
