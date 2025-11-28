# Scraper Agent - Backend

AI-powered web scraping system with Claude-based content extraction, vector embeddings, and semantic search capabilities.

## Overview

Scraper Agent is a production-ready web scraping platform that combines:
- **Intelligent Scraping**: Sitemap-based URL discovery with Playwright browser automation
- **AI Extraction**: Claude Sonnet 4 for structured data extraction
- **Vector Search**: BGE-M3 embeddings with Milvus vector database
- **RAG Pipeline**: 3-stage retrieval-augmented generation for natural language Q&A

## Features

- **FastAPI REST API** with async/await architecture
- **Real-time WebSocket** updates for scraping progress
- **Specialized Agents**: Gym-optimized and general-purpose extractors
- **Vector Embeddings**: BGE-M3 model (1024-dim dense vectors)
- **Semantic Search**: Milvus vector database with HNSW indexing
- **RAG Q&A**: Claude-powered natural language question answering
- **Session Management**: Persistent storage with metadata tracking
- **Full Type Safety**: Pydantic models throughout

---

## Architecture & Docker Setup

### Important: Hybrid Deployment Model

**Docker is used ONLY for the Milvus vector database infrastructure** (etcd, MinIO, Milvus). The **FastAPI backend must run locally** due to a PyTorch segmentation fault issue in containerized environments.

#### Why This Setup?

- **Milvus (Docker)**: Runs in containers for easy management and isolation
- **Backend (Local)**: Runs natively to avoid PyTorch/BGE-M3 model loading issues

> **Note**: The Dockerfile exists for reference but attempting to run the backend in Docker will result in segmentation faults when loading the BGE-M3 embedding model. This is a known issue with PyTorch in certain containerized environments and requires further investigation to resolve.

### Docker Services (Vector Database Only)

The `docker-compose.yml` orchestrates **3 services** for Milvus:

1. **etcd** (milvus-etcd): Metadata storage for Milvus
2. **MinIO** (milvus-minio): Object storage backend for Milvus
3. **Milvus** (milvus-standalone): Vector database server

**Start Milvus Stack:**
```bash
cd backend
docker-compose up -d
```

**Verify Milvus Health:**
```bash
curl http://localhost:9091/healthz
```

---

## Prerequisites

- **Python 3.11+**
- **Docker & Docker Compose** (for Milvus)
- **Anthropic API Key** (get from https://console.anthropic.com/)
- **System Requirements**:
  - Minimum: 4GB RAM, 10GB disk space
  - Recommended: 8GB RAM, 20GB disk space

---

## Installation & Setup

### 1. Clone Repository

```bash
git clone <repository-url>
cd scraper-agent/backend
```

### 2. Create Virtual Environment

```bash
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Playwright Browser

```bash
playwright install chromium
```

### 5. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` and add your Anthropic API key:
```bash
ANTHROPIC_API_KEY=sk-ant-...
```

### 6. Start Milvus (Docker)

```bash
docker-compose up -d
```

### 7. Start Backend (Local)

```bash
# Development mode with auto-reload
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### 8. Verify Installation

```bash
# Check API health
curl http://localhost:8000/health

# Check Milvus connection
curl http://localhost:8000/api/query/health
```

**Access Points:**
- **API**: http://localhost:8000
- **Interactive Docs (Swagger)**: http://localhost:8000/docs
- **Alternative Docs (ReDoc)**: http://localhost:8000/redoc
- **Milvus Health**: http://localhost:9091/healthz
- **MinIO Console**: http://localhost:9001 (minioadmin/minioadmin)

---

## API Endpoints Reference

### Quick Reference Table

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/scrape` | Create general scraping session |
| POST | `/api/scrape/gym` | Create gym-specialized scraping session |
| GET | `/api/sessions` | List all sessions |
| GET | `/api/sessions/{id}` | Get session details & progress |
| DELETE | `/api/sessions/{id}` | Delete session |
| POST | `/api/embed/` | Embed scraped content into vector DB |
| POST | `/api/query/search` | Vector similarity search |
| POST | `/api/query/ask` | Natural language Q&A (RAG) |
| GET | `/api/query/health` | Check vector DB health |
| WS | `/ws/{session_id}` | Real-time scraping updates |
| GET | `/health` | API health check |
| GET | `/` | API info & version |

---

### Scraping Endpoints

<details>
<summary><b>POST /api/scrape</b> - Create General Scraping Session</summary>

**Purpose**: Scrape a website using general-purpose agents

**Request Body:**
```json
{
  "url": "https://example.com",
  "purpose": "Extract contact information and business hours",
  "mode": "whole-site",
  "schema": null
}
```

**Parameters:**
- `url` (required): Target website URL
- `purpose` (optional): Extraction purpose for schema generation
- `mode` (required): `"single-page"` or `"whole-site"`
- `schema` (optional): Custom extraction schema (auto-generated if not provided)

**Response:**
```json
{
  "session_id": "20231128_140530_abc123",
  "status": "pending",
  "message": "Scraping session created successfully. Processing in background.",
  "websocket_url": "ws://localhost:8000/ws/20231128_140530_abc123"
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/scrape \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "purpose": "Extract all contact information",
    "mode": "whole-site"
  }'
```

</details>

<details>
<summary><b>POST /api/scrape/gym</b> - Create Gym-Specialized Scraping Session</summary>

**Purpose**: Scrape gym/fitness websites using specialized agents optimized for gym data

**Request Body:**
```json
{
  "url": "https://mygym.com",
  "purpose": "Extract gym classes, hours, pricing, amenities",
  "mode": "whole-site"
}
```

**Response:** Same format as `/api/scrape`

**Example:**
```bash
curl -X POST http://localhost:8000/api/scrape/gym \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://fitfactoryfitness.com",
    "mode": "whole-site"
  }'
```

**What's Different:**
- Uses gym-optimized schema generator
- Uses gym-specialized content extractor
- Automatically extracts: classes, amenities, pricing, hours, location, trainers

</details>

---

### Session Management Endpoints

<details>
<summary><b>GET /api/sessions</b> - List All Sessions</summary>

**Purpose**: Retrieve all scraping sessions with their current status

**Response:**
```json
{
  "sessions": [
    {
      "session_id": "20231128_140530_abc123",
      "status": "completed",
      "created_at": "2023-11-28T14:05:30",
      "updated_at": "2023-11-28T14:06:45",
      "url": "https://example.com",
      "purpose": "Extract contact information",
      "mode": "whole-site",
      "pages_scraped": 15,
      "total_pages": 15
    }
  ],
  "total": 1
}
```

**Example:**
```bash
curl http://localhost:8000/api/sessions
```

</details>

<details>
<summary><b>GET /api/sessions/{session_id}</b> - Get Session Details</summary>

**Purpose**: Get detailed information about a specific session, including progress

**Response:**
```json
{
  "session_id": "20231128_140530_abc123",
  "status": "in_progress",
  "pages_scraped": 7,
  "total_pages": 15,
  "url": "https://example.com",
  "created_at": "2023-11-28T14:05:30",
  "updated_at": "2023-11-28T14:05:45",
  "error_message": null
}
```

**Status Values:**
- `pending`: Session created, not started
- `in_progress`: Currently scraping
- `completed`: Successfully finished
- `failed`: Encountered error

**Example:**
```bash
curl http://localhost:8000/api/sessions/20231128_140530_abc123
```

</details>

<details>
<summary><b>DELETE /api/sessions/{session_id}</b> - Delete Session</summary>

**Purpose**: Delete a session and all associated data

**Response:**
```json
{
  "message": "Session 20231128_140530_abc123 deleted successfully"
}
```

**Example:**
```bash
curl -X DELETE http://localhost:8000/api/sessions/20231128_140530_abc123
```

</details>

---

### Embedding Endpoints

<details>
<summary><b>POST /api/embed/</b> - Embed Scraped Content</summary>

**Purpose**: Generate vector embeddings for scraped content and store in Milvus

**Request Body (Option 1 - Session ID):**
```json
{
  "session_id": "20231128_140530_abc123"
}
```

**Request Body (Option 2 - Filename):**
```json
{
  "filename": "example.com__20231128_140530_abc123.json"
}
```

**Response:**
```json
{
  "status": "completed",
  "message": "Successfully embedded 15 pages with 127 total chunks",
  "total_pages": 15,
  "total_chunks": 127
}
```

**What It Does:**
1. Loads cleaned markdown from storage
2. Chunks content into 4000-char segments
3. Generates BGE-M3 embeddings (1024-dim vectors)
4. Stores in Milvus with metadata (domain, gym_name, page_name, etc.)

**Example:**
```bash
curl -X POST http://localhost:8000/api/embed/ \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "20231128_140530_abc123"
  }'
```

</details>

---

### Query & RAG Endpoints

<details>
<summary><b>POST /api/query/search</b> - Vector Similarity Search</summary>

**Purpose**: Direct vector search over embedded content (returns raw chunks)

**Request Body:**
```json
{
  "query": "yoga classes morning schedule",
  "top_k": 10,
  "filter_domain": "mygym.com",
  "filter_gym": "Gold's Gym"
}
```

**Parameters:**
- `query` (required): Search query text
- `top_k` (optional, default=5, max=50): Number of results
- `filter_domain` (optional): Filter by website domain
- `filter_gym` (optional): Filter by gym name

**Response:**
```json
{
  "query": "yoga classes morning schedule",
  "results": [
    {
      "chunk_id": "mygym.com_classes_0",
      "domain": "mygym.com",
      "gym_name": "Gold's Gym",
      "page_name": "Classes",
      "page_url": "https://mygym.com/classes",
      "chunk_text": "Yoga classes available Monday-Friday at 6:30am...",
      "score": 0.92
    }
  ],
  "total_results": 1
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/query/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "boxing classes heavy bag",
    "top_k": 5
  }'
```

</details>

<details>
<summary><b>POST /api/query/ask</b> - Natural Language Q&A (RAG)</summary>

**Purpose**: Ask natural language questions and get Claude-powered answers with citations

**3-Stage RAG Pipeline:**
1. **Query Rewriting**: Claude Haiku optimizes query for semantic search
2. **Vector Search**: Retrieves top-k relevant chunks using BGE-M3
3. **Answer Synthesis**: Claude Sonnet generates natural language response

**Request Body:**
```json
{
  "question": "What yoga classes does Gold's Gym offer and when?",
  "conversation_history": [],
  "top_k": 10,
  "filter_gym": "Gold's Gym"
}
```

**Parameters:**
- `question` (required): Natural language question
- `conversation_history` (optional): Previous messages for multi-turn conversation
- `top_k` (optional, default=10): Number of chunks to retrieve
- `filter_domain` (optional): Filter by domain
- `filter_gym` (optional): Filter by gym name

**Response:**
```json
{
  "question": "What yoga classes does Gold's Gym offer and when?",
  "answer": "Gold's Gym offers several yoga classes throughout the week:\n\n1. **Morning Flow Yoga** - Monday, Wednesday, Friday at 6:30 AM\n2. **Hot Yoga** - Tuesday and Thursday at 7:00 AM\n3. **Evening Restorative Yoga** - Monday and Wednesday at 6:30 PM\n\nAll classes are included with membership and are taught by certified instructors.",
  "optimized_query": "yoga classes schedule Gold's Gym times",
  "sources_used": 3,
  "sources": [
    {
      "gym_name": "Gold's Gym",
      "page_name": "Classes Schedule",
      "page_url": "https://mygym.com/classes",
      "score": 0.95
    }
  ]
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/query/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Do you have showers and locker rooms?",
    "top_k": 10
  }'
```

**Multi-Turn Conversation:**
```bash
curl -X POST http://localhost:8000/api/query/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What about pricing?",
    "conversation_history": [
      {"role": "user", "content": "Do you have showers?"},
      {"role": "assistant", "content": "Yes, we have full locker rooms..."}
    ],
    "top_k": 10
  }'
```

</details>

<details>
<summary><b>GET /api/query/health</b> - Vector Database Health Check</summary>

**Purpose**: Verify Milvus connection and collection status

**Response:**
```json
{
  "status": "healthy",
  "service": "vector_search",
  "collection": "gym_sites"
}
```

**Example:**
```bash
curl http://localhost:8000/api/query/health
```

</details>

---

### WebSocket Endpoint

<details>
<summary><b>WS /ws/{session_id}</b> - Real-Time Scraping Updates</summary>

**Purpose**: Receive live progress updates during scraping

**Connection Message:**
```json
{
  "type": "connected",
  "session_id": "20231128_140530_abc123",
  "message": "WebSocket connected"
}
```

**Example (JavaScript):**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/20231128_140530_abc123');

ws.onmessage = (event) => {
  const update = JSON.parse(event.data);
  console.log('Progress:', update);
};

ws.onopen = () => console.log('Connected to session updates');
ws.onerror = (error) => console.error('WebSocket error:', error);
```

**Example (Python):**
```python
import asyncio
import websockets

async def listen_to_session(session_id):
    uri = f"ws://localhost:8000/ws/{session_id}"
    async with websockets.connect(uri) as websocket:
        async for message in websocket:
            print(f"Update: {message}")

asyncio.run(listen_to_session("20231128_140530_abc123"))
```

</details>

---

### Utility Endpoints

<details>
<summary><b>GET /health</b> - API Health Check</summary>

**Response:**
```json
{
  "status": "healthy",
  "service": "scraper-agent"
}
```

**Example:**
```bash
curl http://localhost:8000/health
```

</details>

<details>
<summary><b>GET /</b> - API Information</summary>

**Response:**
```json
{
  "message": "Scraper Agent API",
  "version": "1.0.0",
  "docs": "/docs",
  "health": "/health"
}
```

**Example:**
```bash
curl http://localhost:8000/
```

</details>

---

## Directory Structure

```
backend/
├── src/                              # Source code
│   ├── __init__.py
│   ├── main.py                       # FastAPI app, router registration, WebSocket
│   ├── config.py                     # Environment configuration (Settings class)
│   │
│   ├── models/                       # Pydantic data models
│   │   ├── __init__.py
│   │   ├── session.py                # SessionStatus, ScrapeMode, SessionMetadata
│   │   ├── requests.py               # ScrapeRequest model
│   │   └── responses.py              # API response models
│   │
│   ├── routes/                       # API endpoint handlers
│   │   ├── __init__.py
│   │   ├── scrape.py                 # POST /api/scrape, session status
│   │   ├── gym_scrape.py             # POST /api/scrape/gym (gym-specialized)
│   │   ├── sessions.py               # GET /sessions, DELETE /sessions/{id}
│   │   ├── embed.py                  # POST /api/embed/ (vector embeddings)
│   │   └── query.py                  # POST /query/search, POST /query/ask (RAG)
│   │
│   ├── services/                     # Business logic & external integrations
│   │   ├── __init__.py
│   │   ├── storage_service.py        # File I/O, session directory management
│   │   ├── session_manager.py        # Session lifecycle tracking & metadata
│   │   ├── vector_service.py         # Milvus client + BGE-M3 embeddings
│   │   ├── http_client.py            # HTTP requests (httpx)
│   │   ├── browser_client.py         # Playwright browser automation
│   │   ├── sitemap_discovery.py      # robots.txt → sitemap URL discovery
│   │   ├── html_cleaner.py           # HTML to markdown conversion
│   │   ├── url_queue.py              # URL queue management (Phase 2)
│   │   ├── web_search.py             # Web search integration (Phase 2)
│   │   └── data_aggregator.py        # Data aggregation utilities
│   │
│   ├── agents/                       # AI agents for scraping
│   │   ├── __init__.py
│   │   ├── orchestrator.py           # Main orchestrator (sitemap scraping workflow)
│   │   ├── schema_generator.py       # General schema generation (Claude)
│   │   ├── content_extractor.py      # General content extraction (Claude)
│   │   │
│   │   ├── base/                     # Base agent classes
│   │   │   ├── __init__.py
│   │   │   ├── base_schema_generator.py      # Abstract schema generator
│   │   │   └── base_content_extractor.py     # Abstract content extractor
│   │   │
│   │   └── specialized/              # Domain-specific agents
│   │       ├── __init__.py
│   │       ├── gym_schema_generator.py       # Gym-optimized schema generation
│   │       └── gym_content_extractor.py      # Gym-optimized extraction
│   │
│   ├── schemas/                      # Domain-specific schemas
│   │   ├── __init__.py
│   │   └── gym_schema.py             # Gym/fitness facility schema template
│   │
│   ├── cli/                          # Command-line tools
│   │   ├── __init__.py
│   │   ├── scrape.py                 # CLI scraping command
│   │   └── embed_sites.py            # CLI embedding command (--list, --all, --file)
│   │
│   └── utils/                        # Utility functions
│       ├── __init__.py
│       └── logger.py                 # Structured logging configuration
│
├── tests/                            # Test suite
│   ├── __init__.py
│   ├── test_routes.py                # API endpoint tests
│   ├── test_services.py              # Service layer tests
│   └── test_agents.py                # Agent tests
│
├── data/                             # Session storage (created at runtime)
│   └── {session_id}/
│       ├── metadata.json             # Session metadata
│       ├── request.json              # Original request
│       ├── raw_html.json             # Raw HTML data
│       └── cleaned_markdown/
│           └── {domain}_{timestamp}.json
│
├── etcd_data/                        # etcd persistence (Docker volume)
├── minio_data/                       # MinIO object storage (Docker volume)
├── milvus_data/                      # Milvus vector DB storage (Docker volume)
├── models/                           # BGE-M3 model cache (created at runtime)
│
├── requirements.txt                  # Python dependencies
├── Dockerfile                        # Docker image (reference only - see note above)
├── docker-compose.yml                # Milvus stack orchestration
├── .env                              # Environment variables (ANTHROPIC_API_KEY, etc.)
├── .env.example                      # Example environment file
├── .dockerignore                     # Files excluded from Docker build
└── README.md                         # This file
```

### Key Directories Explained

#### **`src/agents/`** - AI Agents
- **`orchestrator.py`**: Main workflow controller (Phase 1: sitemap-based scraping)
- **`base/`**: Abstract base classes for extensibility
- **`specialized/`**: Domain-specific agents (gym-optimized extractors)

#### **`src/services/`** - Core Services
- **`storage_service.py`**: File system operations, session directories
- **`session_manager.py`**: Session lifecycle, metadata tracking, progress updates
- **`vector_service.py`**: Milvus client, BGE-M3 embeddings, HNSW indexing
- **`browser_client.py`**: Playwright browser automation, HTML fetching
- **`html_cleaner.py`**: HTML → Markdown conversion (BeautifulSoup, markdownify)

#### **`src/routes/`** - API Handlers
Each file corresponds to a route group and handles request validation, background tasks, and response formatting.

#### **`src/cli/`** - Command-Line Tools
- **`embed_sites.py`**: Batch embedding tool (`--list`, `--all`, `--file`, `--recreate`)

---

## Workflows

### 1. Scraping Workflow
```
User Request
    ↓
POST /api/scrape (creates session)
    ↓
Orchestrator Agent
    ↓
Sitemap Discovery (robots.txt → sitemaps)
    ↓
URL Queue (all discovered URLs)
    ↓
Parallel Scraping (Playwright)
    ↓
HTML → Markdown Conversion
    ↓
Save to Storage (data/{session_id}/)
    ↓
Session Status: completed
```

### 2. Embedding Workflow
```
POST /api/embed/ {session_id}
    ↓
Load cleaned markdown from storage
    ↓
Intelligent Chunking (4000 chars, overlap 200)
    ↓
BGE-M3 Embedding Generation (1024-dim vectors)
    ↓
Milvus Insert (with metadata)
    ↓
HNSW Index Creation
    ↓
Return: {total_pages, total_chunks}
```

### 3. RAG Query Workflow
```
POST /api/query/ask {question}
    ↓
Stage 1: Query Rewriting (Claude Haiku)
    ↓
Optimized Query: "yoga classes schedule times"
    ↓
Stage 2: Vector Search (BGE-M3 + Milvus)
    ↓
Top-K Relevant Chunks Retrieved
    ↓
Stage 3: Answer Synthesis (Claude Sonnet)
    ↓
Natural Language Answer + Citations
    ↓
Return: {answer, sources, optimized_query}
```

---

## Environment Configuration

### Required Variables

```bash
ANTHROPIC_API_KEY=sk-ant-...       # Claude API key (required)
```

### Optional Variables

```bash
# Server Configuration
HOST=0.0.0.0                       # API host
PORT=8000                          # API port
DEBUG=False                        # Debug mode

# Storage
STORAGE_BASE_PATH=./data           # Session data directory

# Milvus Configuration
MILVUS_HOST=localhost              # Milvus server host
MILVUS_PORT=19530                  # Milvus gRPC port

# Browser Configuration
BROWSER_TIMEOUT=60                 # Page load timeout (seconds)
BROWSER_WAIT_FOR=networkidle       # Wait strategy: networkidle, load, domcontentloaded
MAX_CONCURRENT_BROWSERS=3          # Max parallel browser instances

# Agent Configuration
MAX_PARALLEL_EXTRACTIONS=3         # Max parallel Claude API calls
MAX_CONCURRENT_EXTRACTIONS=5       # Max concurrent extraction tasks
DEFAULT_TIMEOUT=30                 # Default operation timeout

# Crawling Configuration
MAX_PAGES_PER_SITE=1000            # Max pages to scrape per site
MAX_CRAWL_DEPTH=3                  # Max crawl depth
ENABLE_SITEMAP_CRAWL=True          # Enable sitemap-based discovery
```

---

## CLI Tools

### Embedding CLI

```bash
# List all available cleaned markdown files
python -m src.cli.embed_sites --list

# Embed all files
python -m src.cli.embed_sites --all

# Embed specific file
python -m src.cli.embed_sites --file example.com__20231128_140530.json

# Recreate collection (deletes existing vectors)
python -m src.cli.embed_sites --all --recreate
```

---

## Testing

### Run All Tests

```bash
pytest
```

### Run with Coverage

```bash
pytest --cov=src --cov-report=html
open htmlcov/index.html
```

### Run Specific Test File

```bash
pytest tests/test_services.py
pytest tests/test_routes.py -v
```

---

## Troubleshooting

### Issue: Module not found errors

**Solution:**
```bash
# Ensure you're in backend directory
cd backend

# Activate virtual environment
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements.txt
```

### Issue: Milvus connection refused

**Solution:**
```bash
# Check Milvus is running
docker ps | grep milvus

# Start Milvus stack
docker-compose up -d

# Check Milvus health
curl http://localhost:9091/healthz

# View Milvus logs
docker logs milvus-standalone
```

### Issue: PyTorch segmentation fault in Docker

**Cause:** Known issue with PyTorch/BGE-M3 model loading in containerized environments.

**Solution:** Run the backend locally (not in Docker). Milvus continues to run in Docker.

```bash
# Run backend locally
source venv/bin/activate
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

### Issue: API key errors

**Solution:**
```bash
# Check .env file exists
ls -la .env

# Verify ANTHROPIC_API_KEY is set
cat .env | grep ANTHROPIC_API_KEY

# Test API key
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: $ANTHROPIC_API_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model":"claude-3-haiku-20240307","max_tokens":10,"messages":[{"role":"user","content":"Hi"}]}'
```

### Issue: Storage path errors

**Solution:**
```bash
# Check storage path
echo $STORAGE_BASE_PATH

# Create data directory
mkdir -p data

# Check permissions
ls -ld data
```

### Issue: Playwright browser not found

**Solution:**
```bash
# Install Playwright browsers
playwright install chromium

# Install system dependencies (Linux)
playwright install-deps chromium
```

---

## Development Guide

### Code Style

- **Type Hints**: All functions must have complete type annotations
- **Pydantic Models**: Use for all request/response validation
- **Async/Await**: Use for all I/O operations
- **Structured Logging**: Use `logger` from `src/utils/logger.py`

### Adding New Features

1. **Define Models** in `src/models/`
2. **Implement Services** in `src/services/`
3. **Create Routes** in `src/routes/`
4. **Write Tests** in `tests/`
5. **Update Documentation** in this README

### Adding New Agents

1. **Create Subclass** in `src/agents/specialized/`
2. **Inherit** from `BaseSchemaGenerator` or `BaseContentExtractor`
3. **Implement** required abstract methods
4. **Register** in route handler

Example:
```python
from src.agents.base.base_content_extractor import BaseContentExtractor

class RestaurantExtractor(BaseContentExtractor):
    def _get_system_prompt(self) -> str:
        return "Extract restaurant information..."

    def _get_user_prompt(self, html: str, schema: dict) -> str:
        return f"Extract from: {html[:1000]}"
```

---

## Key Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `fastapi` | 0.104.1 | Web framework |
| `uvicorn` | 0.24.0 | ASGI server |
| `pydantic` | 2.5.0 | Data validation |
| `anthropic` | 0.72.0 | Claude API client |
| `httpx` | 0.25.1 | Async HTTP client |
| `playwright` | 1.40.0 | Browser automation |
| `pymilvus` | 2.3.4 | Vector database client |
| `FlagEmbedding` | 1.2.3 | BGE-M3 embeddings |
| `beautifulsoup4` | 4.12.2 | HTML parsing |
| `lxml` | 4.9.3 | XML/HTML processing |
| `typer` | 0.9.0 | CLI framework |
| `rich` | 13.7.0 | Terminal formatting |

---

## Production Deployment

### Recommendations

1. **Use a process manager** (systemd, supervisor) for the backend
2. **Set up reverse proxy** (nginx) for HTTPS
3. **Configure firewall** to restrict Milvus ports
4. **Use environment-specific .env files**
5. **Set up monitoring** (health check endpoints)
6. **Configure log rotation**
7. **Set up backup strategy** for Milvus data

### Example systemd Service

```ini
[Unit]
Description=Scraper Agent Backend
After=docker.service
Requires=docker.service

[Service]
Type=simple
User=scraper
WorkingDirectory=/opt/scraper-agent/backend
Environment="PATH=/opt/scraper-agent/backend/venv/bin"
ExecStart=/opt/scraper-agent/backend/venv/bin/python -m uvicorn src.main:app --host 0.0.0.0 --port 8000
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

---

## Future Work

- [ ] Resolve PyTorch Docker containerization issue
- [ ] Implement full Phase 2: Multi-page discovery with intelligent crawling
- [ ] Add authentication & API key management
- [ ] Implement rate limiting
- [ ] Add caching layer for frequent queries
- [ ] Support for scheduled/recurring scrapes
- [ ] Web UI for monitoring and management

---

## License

[Specify your license here]

---

## Support

For issues and questions:
- Check `/docs` endpoint for interactive API documentation
- Review logs in terminal output
- Check Milvus logs: `docker logs milvus-standalone`
- Verify environment variables in `.env`
