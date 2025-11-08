# Phase 1 Implementation Plan: Core Backend Infrastructure

## Tech Stack
- **Backend**: Python 3.11+ with FastAPI
- **Type Safety**: Full type hints with Pydantic models
- **Agent SDK**: Claude Agent SDK (Anthropic)
- **HTTP Client**: httpx (async support)
- **WebSocket**: FastAPI's built-in WebSocket support
- **Testing**: pytest with pytest-asyncio
- **Project Structure**: Standard production patterns with separation of concerns

## Project Structure
```
scraper-agent/
├── backend/
│   ├── src/
│   │   ├── __init__.py
│   │   ├── main.py                    # FastAPI app entry point
│   │   ├── config.py                  # Configuration management
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── requests.py            # Request models (Pydantic)
│   │   │   ├── responses.py           # Response models
│   │   │   └── session.py             # Session data models
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── scrape.py              # Scraping endpoints
│   │   │   └── sessions.py            # Session management endpoints
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── session_manager.py     # Session lifecycle
│   │   │   ├── storage_service.py     # File system operations
│   │   │   └── http_client.py         # URL fetching
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   ├── orchestrator.py        # Main agent
│   │   │   ├── schema_generator.py    # Schema generation subagent
│   │   │   └── content_extractor.py   # Content extraction subagent
│   │   └── utils/
│   │       ├── __init__.py
│   │       └── logger.py              # Logging utilities
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_routes.py
│   │   ├── test_agents.py
│   │   └── test_services.py
│   ├── requirements.txt
│   ├── requirements-dev.txt
│   └── pytest.ini
├── PHASES.md
└── README.md
```

## Implementation Steps

### Step 1: Project Initialization (30 min)
1. Create `backend/` directory structure
2. Initialize Python virtual environment
3. Create `requirements.txt` with core dependencies:
   - fastapi
   - uvicorn[standard]
   - pydantic
   - anthropic (Claude SDK)
   - httpx
   - python-dotenv
4. Create `requirements-dev.txt` with dev dependencies:
   - pytest
   - pytest-asyncio
   - httpx (for testing)
5. Set up `.env` file for API keys
6. Create `.gitignore` for Python

### Step 2: Configuration & Models (1 hour)
1. **config.py**: Environment variables, storage paths, API settings
2. **models/requests.py**: `ScrapeRequest` model (url, purpose, schema, mode)
3. **models/responses.py**: `ScrapeResponse`, `SessionResponse` models
4. **models/session.py**: `Session`, `SessionMetadata`, `SessionStatus` enums

### Step 3: Storage Service (1.5 hours)
1. **storage_service.py**:
   - Create session directories in `~/Downloads/scraper-agent/`
   - Save/load JSON files (metadata, request, schema, extracted_data)
   - Generate session IDs with timestamps
   - List sessions
   - Retrieve session data

### Step 4: Session Manager (1.5 hours)
1. **session_manager.py**:
   - Initialize new sessions
   - Track session lifecycle (pending → in_progress → completed/failed)
   - Update session status
   - Store session metadata
   - In-memory session tracking (dict-based for Phase 1)

### Step 5: HTTP Client Service (45 min)
1. **http_client.py**:
   - Async URL fetching with httpx
   - Error handling (404, timeouts, etc.)
   - Return HTML content
   - Basic retry logic

### Step 6: Schema Generator Subagent (2 hours)
1. **schema_generator.py**:
   - Initialize Claude client
   - Create prompt for schema generation
   - Input: purpose + HTML sample
   - Use Claude API to generate JSON schema
   - Parse and validate schema output
   - Return structured schema dict

### Step 7: Content Extractor Subagent (2 hours)
1. **content_extractor.py**:
   - Initialize Claude client
   - Create extraction prompt with schema + HTML
   - Use Claude API to extract data
   - Parse extracted data
   - Validate against schema
   - Return extracted data as dict

### Step 8: Main Orchestrator Agent (2.5 hours)
1. **orchestrator.py**:
   - Initialize Claude Agent SDK
   - Orchestrate workflow:
     - Fetch URL content
     - Generate schema (if not provided)
     - Extract content using schema
     - Aggregate results
   - Handle errors at each step
   - Update session status throughout process

### Step 9: API Routes (2 hours)
1. **routes/scrape.py**:
   - `POST /api/scrape`: Accept scrape requests, create session, trigger orchestrator
   - Async endpoint handlers
   - Request validation with Pydantic
2. **routes/sessions.py**:
   - `GET /api/sessions`: List all sessions
   - `GET /api/sessions/{session_id}`: Get specific session
   - `DELETE /api/sessions/{session_id}`: Delete session

### Step 10: WebSocket Setup (1.5 hours)
1. **main.py** - Add WebSocket endpoint:
   - `/ws/{session_id}`: Connect to session updates
   - Broadcast status changes
   - Send progress messages
   - Handle client connections

### Step 11: FastAPI App Setup (1 hour)
1. **main.py**:
   - Initialize FastAPI app
   - Register routes
   - Add CORS middleware
   - Configure WebSocket
   - Add error handlers
   - Health check endpoint

### Step 12: Testing Infrastructure (2.5 hours)
1. **pytest.ini**: Configure pytest
2. **test_routes.py**: Test all API endpoints
3. **test_agents.py**: Test orchestrator and subagents
4. **test_services.py**: Test storage and session management
5. Mock Claude API responses for testing

### Step 13: Integration & Testing (2 hours)
1. Test complete flow with curl/Postman
2. Verify session creation and storage
3. Test schema generation with real URLs
4. Test content extraction
5. Verify WebSocket connections
6. Fix bugs and edge cases

## Success Validation Checklist
- [ ] `POST /api/scrape` accepts requests and creates sessions
- [ ] Agent fetches URL content successfully
- [ ] Schema auto-generation works with various HTML structures
- [ ] Content extraction maps data to schema correctly
- [ ] Results saved to `~/Downloads/scraper-agent/{session_id}/`
- [ ] Can retrieve session data via `GET /api/sessions/{session_id}`
- [ ] WebSocket broadcasts status updates
- [ ] All pytest tests pass
- [ ] Can test with curl: `curl -X POST http://localhost:8000/api/scrape -H "Content-Type: application/json" -d '{"url":"https://example.com","purpose":"Extract contact info"}'`

## Estimated Timeline
- **Total**: ~18 hours of focused development
- **With testing/debugging**: 2-3 full work days
- **Part-time (evenings)**: 4-6 days

## Next Steps After Approval
1. Create directory structure
2. Initialize virtual environment
3. Install dependencies
4. Start with Step 1 (Project Initialization)
5. Work through steps sequentially with testing at each stage
