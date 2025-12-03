# HuggingFace Spaces Migration Plan

## Overview
Migrate the Agentic Scraper backend from Milvus to a Spaces-optimized stack using ChromaDB + ZeroGPU for better performance and simpler deployment.

## Current Architecture Issues for Spaces

### Problems:
1. **Milvus Server**: Requires separate service process, heavy memory footprint
2. **CPU-bound Embeddings**: BGE-M3 model runs slowly on CPU (2-3s per chunk)
3. **Complex Deployment**: Multiple services (FastAPI + Milvus + Gradio)
4. **Resource Constraints**: Spaces has limited resources for persistent services

### Current Stack:
- **Vector DB**: Milvus standalone (pymilvus)
- **Embeddings**: BGE-M3 via FlagEmbedding (CPU)
- **API**: FastAPI backend on port 8000
- **Frontend**: Gradio on port 7860

## Recommended Architecture for Spaces

### New Stack:
- **Vector DB**: ChromaDB (persistent, file-based)
- **Embeddings**: BGE-M3 with ZeroGPU acceleration
- **API**: FastAPI backend on port 8000
- **Frontend**: Gradio on port 7860

### Key Improvements:
1. **No Milvus Server**: ChromaDB is Python-native, no separate process
2. **GPU-Accelerated**: ZeroGPU gives 10-50x speedup for embeddings
3. **Cost-Effective**: ZeroGPU is pay-per-use (only charged when running)
4. **Persistent**: ChromaDB stores on disk (survives Space restarts)
5. **Simpler**: Fewer dependencies, easier debugging

## Implementation Plan

### Phase 1: Create ChromaDB Vector Service

#### File: `backend/src/services/vector_service_chroma.py`

**Actions**:
1. Create new `VectorServiceChroma` class
2. Implement same interface as current `VectorService`
3. Add ZeroGPU decorators to embedding functions

**Key Implementation**:
```python
import chromadb
import spaces
from typing import List, Dict, Any, Optional
from FlagEmbedding import BGEM3FlagModel

class VectorServiceChroma:
    def __init__(self, collection_name: str = "scraped_sites"):
        # Persistent ChromaDB client (survives restarts)
        self.client = chromadb.PersistentClient(path="./chroma_db")

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "ip"}  # Inner product (cosine similarity)
        )

        # BGE-M3 model
        self.model: Optional[BGEM3FlagModel] = None

    def load_model(self):
        """Load BGE-M3 embedding model."""
        if self.model is None:
            import torch
            torch.set_num_threads(1)
            self.model = BGEM3FlagModel('BAAI/bge-m3', use_fp16=True)

    @spaces.GPU  # ZeroGPU: GPU allocated only when this runs
    def embed_text(self, text: str) -> List[float]:
        """Embed text using BGE-M3 with GPU acceleration.

        This function runs on GPU via ZeroGPU decorator.
        """
        if self.model is None:
            self.load_model()

        embeddings = self.model.encode(
            [text],
            return_dense=True,
            return_sparse=False,
            return_colbert_vecs=False
        )

        return embeddings['dense_vecs'][0].tolist()

    @spaces.GPU  # Batch embedding also uses GPU
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple texts in batch (more efficient)."""
        if self.model is None:
            self.load_model()

        embeddings = self.model.encode(
            texts,
            return_dense=True,
            return_sparse=False,
            return_colbert_vecs=False
        )

        return embeddings['dense_vecs'].tolist()

    def insert_chunks(
        self,
        domain: str,
        site_name: str,
        page_name: str,
        page_url: str,
        chunks: List[Dict[str, str]]
    ):
        """Insert chunked text into ChromaDB."""
        if not chunks:
            return

        # Prepare data
        ids = []
        embeddings = []
        metadatas = []
        documents = []

        # Extract texts for batch embedding
        texts = [chunk["text"] for chunk in chunks]

        # Batch embed (GPU-accelerated)
        embeddings = self.embed_batch(texts)

        # Prepare for ChromaDB insertion
        for i, chunk in enumerate(chunks):
            chunk_id = f"{domain}_{page_name}_{i}"
            ids.append(chunk_id)
            documents.append(chunk["text"][:8000])  # ChromaDB limit
            metadatas.append({
                "domain": domain,
                "site_name": site_name,
                "page_name": page_name,
                "page_url": page_url,
                "chunk_id": chunk_id
            })

        # Insert into ChromaDB
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents
        )

    def search(
        self,
        query: str,
        top_k: int = 20,
        filter_domain: Optional[str] = None,
        filter_site: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search using GPU-accelerated query embedding."""
        # Embed query (GPU-accelerated)
        query_embedding = self.embed_text(query)

        # Build filter
        where_filter = {}
        if filter_domain:
            where_filter["domain"] = filter_domain
        if filter_site:
            where_filter["site_name"] = filter_site

        # Search
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_filter if where_filter else None
        )

        # Format results
        formatted_results = []
        for i in range(len(results['ids'][0])):
            formatted_results.append({
                "chunk_id": results['metadatas'][0][i]["chunk_id"],
                "domain": results['metadatas'][0][i]["domain"],
                "site_name": results['metadatas'][0][i]["site_name"],
                "page_name": results['metadatas'][0][i]["page_name"],
                "page_url": results['metadatas'][0][i]["page_url"],
                "chunk_text": results['documents'][0][i],
                "score": results['distances'][0][i],
            })

        return formatted_results

    def delete_by_domain(self, domain: str):
        """Delete all chunks for a domain."""
        self.collection.delete(where={"domain": domain})

# Global instance
vector_service = VectorServiceChroma()
```

### Phase 2: Update Backend Routes

#### File: `backend/src/routes/embed.py`

**Changes**:
```python
# Old import
# from ..services.vector_service import vector_service

# New import
from ..services.vector_service_chroma import vector_service
```

No other changes needed - same interface!

#### File: `backend/src/routes/query.py`

**Changes**:
```python
# Old import
# from ..services import vector_service

# New import
from ..services.vector_service_chroma import vector_service
```

No other changes needed - same interface!

### Phase 3: Update Dependencies

#### File: `backend/requirements.txt`

**Add**:
```
chromadb>=0.4.0
spaces>=0.1.0
```

**Optional - Remove** (if not using Milvus anymore):
```
# pymilvus==2.3.4
```

**Keep**:
```
FlagEmbedding==1.2.3
anthropic==0.72.0
fastapi==0.104.1
uvicorn[standard]==0.24.0
httpx>=0.25.0
playwright>=1.40.0
beautifulsoup4>=4.12.0
markdownify>=0.11.6
python-dotenv>=1.0.0
pydantic>=2.0.0
```

### Phase 4: Docker Configuration for Spaces

#### File: `Dockerfile`

```dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install Playwright browsers
RUN pip install playwright && playwright install --with-deps chromium

# Copy requirements
COPY backend/requirements.txt /app/backend/requirements.txt
COPY frontend/requirements.txt /app/frontend/requirements.txt

# Install Python dependencies
RUN pip install --no-cache-dir -r /app/backend/requirements.txt
RUN pip install --no-cache-dir -r /app/frontend/requirements.txt

# Copy application code
COPY backend /app/backend
COPY frontend /app/frontend

# Create directory for ChromaDB persistence
RUN mkdir -p /app/chroma_db

# Expose ports
EXPOSE 7860 8000

# Copy startup script
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Run startup script
CMD ["/app/start.sh"]
```

#### File: `start.sh`

```bash
#!/bin/bash

# Start FastAPI backend in background
cd /app/backend
uvicorn src.main:app --host 0.0.0.0 --port 8000 &

# Wait for backend to be ready
echo "Waiting for backend to start..."
sleep 5

# Check backend health
curl -s http://localhost:8000/health || echo "Backend health check failed"

# Start Gradio frontend (foreground - keeps container alive)
cd /app/frontend
python app.py
```

#### File: `README.md` (Spaces Header)

```markdown
---
title: Agentic Scraper
emoji: 🤖
colorFrom: orange
colorTo: red
sdk: docker
sdk_version: "4.36.0"
app_port: 7860
---

# Agentic Scraper

AI-powered web scraper with RAG-based Q&A using Claude, ChromaDB, and BGE-M3 embeddings.

## Features
- Scrape entire websites with Playwright
- GPU-accelerated embeddings via ZeroGPU
- Domain-isolated vector search
- Claude-powered natural language Q&A
```

### Phase 5: Environment Configuration

#### File: `.env.example` (for Spaces Secrets)

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...

# Optional (defaults work for most cases)
API_BASE_URL=http://localhost:8000
GRADIO_SERVER_PORT=7860
DEBUG=False
STORAGE_BASE_PATH=/app/data
MAX_PARALLEL_EXTRACTIONS=3
DEFAULT_TIMEOUT=30
```

**Set in Spaces Dashboard**:
- `ANTHROPIC_API_KEY`: Your Claude API key
- Optionally set `STORAGE_BASE_PATH` if you want persistent scraped data

### Phase 6: Testing Migration

#### Local Testing (Without GPU):

```bash
# 1. Install new dependencies
pip install chromadb spaces

# 2. Create test script
python -c "
from backend.src.services.vector_service_chroma import vector_service

# Test embedding
vector = vector_service.embed_text('Hello world')
print(f'Embedding dimension: {len(vector)}')

# Test insert
vector_service.insert_chunks(
    domain='example.com',
    site_name='Example Site',
    page_name='Home',
    page_url='https://example.com',
    chunks=[{'text': 'This is a test chunk'}]
)

# Test search
results = vector_service.search('test', top_k=5)
print(f'Search results: {len(results)}')
"
```

#### Spaces Testing (With ZeroGPU):

1. Push to Spaces repository
2. Monitor build logs
3. Test scraping endpoint: `POST /api/scrape`
4. Test embedding endpoint: `POST /api/embed/`
5. Test query endpoint: `POST /api/query/ask`
6. Verify GPU usage in Spaces dashboard

### Phase 7: Data Migration (If Needed)

#### Option A: Re-scrape everything
- Easiest approach
- Ensures data consistency
- Use admin interface to re-scrape sites

#### Option B: Export from Milvus, Import to ChromaDB

```python
# Export from Milvus
from backend.src.services.vector_service import vector_service as milvus_service

# Get all data
# (Milvus doesn't have bulk export - would need to iterate)

# Import to ChromaDB
from backend.src.services.vector_service_chroma import vector_service as chroma_service

# Insert chunks (same format)
chroma_service.insert_chunks(...)
```

**Recommendation**: Re-scrape for clean migration

## Performance Comparison

### Before (Milvus + CPU):
- **Embedding Speed**: ~2-3 seconds per chunk (CPU)
- **Search Speed**: ~100-200ms
- **Memory Usage**: ~2GB (Milvus server + model)
- **Deployment**: Complex (multiple processes)

### After (ChromaDB + ZeroGPU):
- **Embedding Speed**: ~50-100ms per chunk (GPU)
- **Search Speed**: ~50-100ms
- **Memory Usage**: ~500MB (no separate server)
- **Deployment**: Simple (single process)

**Expected Improvement**: 20-30x faster embeddings, 50% lower memory

## Risks & Mitigations

**Risk 1**: ZeroGPU cold start latency
- **Mitigation**: First request may be slower (~5-10s), then fast. Acceptable for async operations.

**Risk 2**: ChromaDB data persistence
- **Mitigation**: Use PersistentClient with volume mount. Data survives restarts.

**Risk 3**: Breaking existing data
- **Mitigation**: Keep Milvus service running during migration, switch after testing.

**Risk 4**: ZeroGPU quota limits
- **Mitigation**: Monitor usage, optimize batch sizes, cache results where possible.

## Rollback Plan

If migration fails:

1. Revert `backend/src/routes/*.py` imports back to Milvus
2. Remove ChromaDB dependency
3. Restart with original Milvus configuration
4. No data loss (Milvus data unchanged)

## Success Criteria

1. ✅ ChromaDB vector service works locally
2. ✅ All backend tests pass with new service
3. ✅ Spaces deployment builds successfully
4. ✅ ZeroGPU acceleration works (check logs for GPU usage)
5. ✅ Embeddings complete in <200ms per chunk
6. ✅ Search returns correct results with domain filtering
7. ✅ No Milvus dependency in deployed container

## Next Steps After Migration

1. **Optimize Batch Sizes**: Tune batch embedding for max GPU efficiency
2. **Add Caching**: Cache frequently asked questions
3. **Monitor Costs**: Track ZeroGPU usage and optimize
4. **Performance Tuning**: Adjust ChromaDB HNSW parameters
5. **Backup Strategy**: Implement ChromaDB backup/restore
