# Quick Start Guide - Scraper Agent

Phase 1 (Core Backend Infrastructure) is now complete! 🎉

## What's Included

✅ FastAPI REST API with scraping endpoints
✅ WebSocket support for real-time updates
✅ AI-powered schema generation using Claude
✅ Intelligent content extraction
✅ Session management with file system storage
✅ Full test coverage (26 passing tests)
✅ Type-safe Pydantic models

## Getting Started

### 1. Set Up the Backend

```bash
cd backend

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
```

### 2. Add Your API Key

Edit `backend/.env` and add your Anthropic API key:

```
ANTHROPIC_API_KEY=your_api_key_here
```

### 3. Run the Server

```bash
# Option 1: Using the run script
./run.sh

# Option 2: Direct command
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- API: http://localhost:8000
- Interactive Docs: http://localhost:8000/docs

### 4. Test the API

#### Using curl:

```bash
# Create a scraping session
curl -X POST http://localhost:8000/api/scrape \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "purpose": "Extract contact information and business hours"
  }'

# Response:
# {
#   "session_id": "20231108_140530_abc123",
#   "status": "pending",
#   "message": "Scraping session created successfully",
#   "websocket_url": "ws://localhost:8000/ws/20231108_140530_abc123"
# }

# Wait a few seconds for processing, then get results:
curl http://localhost:8000/api/sessions/20231108_140530_abc123
```

#### Using the interactive docs:

1. Open http://localhost:8000/docs
2. Try the `POST /api/scrape` endpoint
3. Use the returned session_id to check results with `GET /api/sessions/{session_id}`

### 5. Run Tests

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html
```

All 26 tests should pass! ✅

## Project Structure

```
scraper-agent/
├── backend/
│   ├── src/
│   │   ├── agents/          # AI agents (orchestrator, schema gen, extractor)
│   │   ├── models/          # Pydantic data models
│   │   ├── routes/          # API endpoints
│   │   ├── services/        # Business logic
│   │   ├── utils/           # Utilities
│   │   ├── config.py        # Configuration
│   │   └── main.py          # FastAPI app
│   ├── tests/               # Test files (26 tests)
│   └── README.md            # Detailed backend docs
├── PHASES.md                # Complete development roadmap
└── Phase-1-Implementation.md # Phase 1 implementation plan
```

## How It Works

1. **Send a scraping request** with a URL and purpose
2. **Schema generation** - Claude analyzes the HTML and generates a data schema
3. **Content extraction** - Claude extracts structured data based on the schema
4. **Results saved** to `~/Downloads/scraper-agent/{session_id}/`

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/scrape` | POST | Create new scraping session |
| `/api/sessions` | GET | List all sessions |
| `/api/sessions/{id}` | GET | Get session details |
| `/api/sessions/{id}` | DELETE | Delete session |
| `/ws/{id}` | WebSocket | Real-time updates |
| `/health` | GET | Health check |

## Example Usage

### Python Example:

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
        session_id = response.json()["session_id"]
        print(f"Session created: {session_id}")

        # Wait for processing
        await asyncio.sleep(10)

        # Get results
        response = await client.get(
            f"http://localhost:8000/api/sessions/{session_id}"
        )
        session = response.json()
        print("Extracted data:", session["extracted_data"])

asyncio.run(scrape_example())
```

## Storage

Scraped data is stored in `~/Downloads/scraper-agent/`:

```
~/Downloads/scraper-agent/
└── 20231108_140530_abc123/
    ├── metadata.json         # Session metadata
    ├── request.json          # Original request
    ├── schema.json           # Generated schema
    ├── extracted_data.json   # Extracted data
    └── sources.json          # Source URLs
```

## Next Steps

Phase 1 is complete! See `PHASES.md` for the complete roadmap.

**Phase 2** (Next): Multi-Page Discovery & Extraction
- URL queue management
- Parallel processing
- Web search integration

**Phase 4+**: Chrome Extension UI
- Sidebar interface
- Browser control
- Live progress display

## Need Help?

- Full backend docs: `backend/README.md`
- API docs: http://localhost:8000/docs
- Implementation plan: `Phase-1-Implementation.md`
- Project phases: `PHASES.md`

## Success Criteria ✅

All Phase 1 success criteria met:

- ✅ `POST /api/scrape` accepts requests and creates sessions
- ✅ Agent fetches URL content successfully
- ✅ Schema auto-generation works with various HTML structures
- ✅ Content extraction maps data to schema correctly
- ✅ Results saved to `~/Downloads/scraper-agent/{session_id}/`
- ✅ Can retrieve session data via `GET /api/sessions/{session_id}`
- ✅ WebSocket broadcasts status updates
- ✅ All pytest tests pass (26/26)
- ✅ Can test with curl
