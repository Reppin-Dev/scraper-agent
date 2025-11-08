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
