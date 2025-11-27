# Scraper Agent - Backend

AI-powered web scraping agent with intelligent data extraction using Claude.

## Features

- **FastAPI REST API** for scraping requests
- **WebSocket support** for real-time updates
- **Intelligent schema generation** using Claude AI
- **Automated data extraction** from HTML content
- **Session management** with file system storage
- **Full type safety** with Pydantic models

## Setup

### Prerequisites

- Python 3.11 or higher
- Anthropic API key

### Installation

1. Create and activate virtual environment:
```bash
cd backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create `.env` file:
```bash
cp .env.example .env
```

4. Edit `.env` and add your Anthropic API key:
```
ANTHROPIC_API_KEY=your_api_key_here
```

## Running the Server

### Development Mode

```bash
# Make sure you're in the backend directory with venv activated
cd backend
source venv/bin/activate

# Run the server
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

Or use the run script:
```bash
chmod +x run.sh
./run.sh
```

The API will be available at:
- API: http://localhost:8000
- Interactive Docs: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Docker Deployment

For production deployment or isolated development, use Docker:

**Prerequisites:**
- Docker and Docker Compose installed

**Quick Start:**

1. Create `.env` file with required variables:
```bash
ANTHROPIC_API_KEY=your_api_key_here
MILVUS_HOST=milvus-standalone
MILVUS_PORT=19530
```

2. Start all services:
```bash
docker-compose up -d
```

This will start:
- **FastAPI backend** (port 8000)
- **Milvus vector database** (port 19530)
- **MinIO object storage** (port 9000, console: 9001)
- **etcd** for Milvus metadata

3. Check service status:
```bash
docker-compose ps
```

4. View logs:
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
```

5. Stop services:
```bash
docker-compose down
```

**Access Points:**
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- MinIO Console: http://localhost:9001 (admin/minioadmin)

**Data Persistence:**

Data is persisted in Docker volumes:
- `milvus_data/` - Vector database storage
- `minio_data/` - Object storage
- `etcd_data/` - Metadata storage

**Development with Docker:**

For development with auto-reload:
```bash
# Modify docker-compose.yml to mount source code
docker-compose up backend
```

**Troubleshooting:**

1. Port conflicts: Change ports in `docker-compose.yml`
2. Reset data: `docker-compose down -v` (removes volumes)
3. Rebuild images: `docker-compose build --no-cache`

## CLI Tools

The backend includes powerful CLI tools for scraping and embedding content. See [`src/cli/README.md`](src/cli/README.md) for detailed documentation.

### Scrape CLI

Scrape websites with real-time progress tracking:

```bash
# Scrape a single page
python -m src.cli.scrape https://example.com --mode single-page

# Scrape entire website
python -m src.cli.scrape https://example.com --mode whole-site --purpose "Scrape gym information"
```

Features:
- Real-time progress with spinner and page count
- Elapsed time tracking
- Final summary with scraped URLs
- Session ID for later reference

### Embed Sites CLI

Embed scraped content into Milvus vector database with multi-level progress tracking:

```bash
# List available cleaned markdown files
python -m src.cli.embed_sites list

# Embed all files
python -m src.cli.embed_sites embed

# Embed specific file
python -m src.cli.embed_sites embed --file example.com__20251124.json

# Delete collection
python -m src.cli.embed_sites delete

# Delete specific domain
python -m src.cli.embed_sites delete --domain example.com
```

Features:
- Three-level progress bars (Files → Pages → Chunks)
- BGE-M3 embeddings for semantic search
- Safe deletion with confirmation prompts
- Comprehensive file listing

## API Endpoints

### Scraping

**Create Scrape Session**
```bash
POST /api/scrape
```

Request body:
```json
{
  "url": "https://example.com",
  "purpose": "Extract contact information",
  "mode": "single-page",
  "schema": null  // Optional: provide custom schema
}
```

Response:
```json
{
  "session_id": "20231108_140530_abc123",
  "status": "pending",
  "message": "Scraping session created successfully",
  "websocket_url": "ws://localhost:8000/ws/20231108_140530_abc123"
}
```

### Session Management

**List All Sessions**
```bash
GET /api/sessions
```

**Get Session Details**
```bash
GET /api/sessions/{session_id}
```

**Delete Session**
```bash
DELETE /api/sessions/{session_id}
```

### WebSocket

Connect to real-time updates:
```
ws://localhost:8000/ws/{session_id}
```

## Testing

Run all tests:
```bash
pytest
```

Run with coverage:
```bash
pytest --cov=src --cov-report=html
```

Run specific test file:
```bash
pytest tests/test_services.py
```

## Example Usage

### Using curl

```bash
# Create a scraping session
curl -X POST http://localhost:8000/api/scrape \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "purpose": "Extract contact information and business hours"
  }'

# Get session details
curl http://localhost:8000/api/sessions/{session_id}

# List all sessions
curl http://localhost:8000/api/sessions
```

### Using Python

```python
import httpx
import asyncio

async def scrape_example():
    async with httpx.AsyncClient() as client:
        # Create scraping session
        response = await client.post(
            "http://localhost:8000/api/scrape",
            json={
                "url": "https://example.com",
                "purpose": "Extract contact information"
            }
        )
        data = response.json()
        session_id = data["session_id"]

        # Wait a bit for processing
        await asyncio.sleep(5)

        # Get results
        response = await client.get(
            f"http://localhost:8000/api/sessions/{session_id}"
        )
        session = response.json()
        print(session["extracted_data"])

asyncio.run(scrape_example())
```

## Project Structure

```
backend/
├── src/
│   ├── agents/           # AI agents (orchestrator, schema gen, extractor)
│   ├── models/           # Pydantic data models
│   ├── routes/           # API endpoints
│   ├── services/         # Business logic services
│   ├── utils/            # Utilities (logging, etc.)
│   ├── config.py         # Configuration
│   └── main.py           # FastAPI application
├── tests/                # Test files
├── requirements.txt      # Production dependencies
├── requirements-dev.txt  # Development dependencies
└── pytest.ini           # Pytest configuration
```

## Storage

Scraped data is stored in:
```
~/Downloads/scraper-agent/{session_id}/
├── metadata.json         # Session metadata
├── request.json          # Original request
├── schema.json           # Generated/provided schema
├── extracted_data.json   # Extracted data
└── sources.json          # Source URLs
```

## Development

### Code Style

This project uses:
- Type hints for all functions
- Pydantic for data validation
- Async/await for I/O operations
- Structured logging

### Adding New Features

1. Create models in `src/models/`
2. Implement services in `src/services/`
3. Add routes in `src/routes/`
4. Write tests in `tests/`

## Troubleshooting

**Issue: Module not found errors**
- Make sure you're in the backend directory
- Ensure virtual environment is activated
- Reinstall dependencies: `pip install -r requirements.txt`

**Issue: API key errors**
- Check `.env` file exists and has valid `ANTHROPIC_API_KEY`
- Ensure API key has proper permissions

**Issue: Storage path errors**
- Check `STORAGE_BASE_PATH` in `.env`
- Ensure directory has write permissions

## Next Steps

See `PHASES.md` in the project root for the complete development roadmap.

Phase 1 (Current): Core Backend Infrastructure ✅
- REST API with scraping endpoints
- Session management
- AI-powered schema generation
- Content extraction
- WebSocket support

Phase 2 (Next): Multi-Page Discovery & Extraction
- URL queue management
- Parallel processing
- Web search integration
