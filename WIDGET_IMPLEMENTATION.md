# Plan: Create Embeddable Chatbot Widget from Gradio App

## Overview
Convert the Agentic Scraper Gradio app into an embeddable website widget that:
- Appears as a popup modal chatbot (bottom-right corner)
- Auto-scrapes and embeds the host website's content
- Shows only the chat interface (no scraping UI)
- Deploys to Gradio Spaces with a permanent public URL
- Uses Gradio's JavaScript Client for embedding

## Implementation Strategy

### 1. Create Combined Spaces Deployment with Dockerfile
**Files**: `Dockerfile`, `docker-compose.yml` (new files)

Since both backend and frontend will be deployed together on Gradio Spaces:
- Create Dockerfile that runs both FastAPI backend and Gradio frontend
- Use separate processes (uvicorn for backend, gradio for frontend)
- Backend runs on internal port 8000
- Gradio frontend on port 7860 (Spaces default)
- Milvus vector DB also containerized

**Key components**:
- Multi-stage Docker build
- Process manager (supervisord or simple shell script) to run both services
- Shared volume for scraped data storage
- Environment-based configuration

### 2. Implement Multi-Website Support with Domain Isolation
**Approach**: Use existing domain filtering in backend

The backend already supports domain filtering via `filter_domain` parameter in `/api/query/ask` endpoint (lines 101-102 in query.py).

**Widget Implementation**:
- Each website embedding gets a unique domain identifier
- Widget JavaScript passes the current domain to backend
- Backend filters vector search results by domain
- Each website only queries its own embedded content

**Domain Extraction**:
```javascript
// In widget JavaScript
const currentDomain = window.location.hostname;
// Pass as filter_domain to backend
```

### 3. Create a Chat-Only Gradio Interface
**File**: `frontend/app_embed.py` (new file)

Create a simplified version that:
- Removes all scraping UI components (URL input, scrape button, progress logs)
- Shows only the Chatbot component and message input
- Automatically detects user's domain from request headers
- Passes domain filter to backend for isolated querying
- Maintains the custom dark theme and avatar images

**Key changes from current app.py**:
- No URL input or scraping workflow
- Domain extraction from HTTP headers or query params
- Modified `chat_fn()` to include `filter_domain` parameter
- Simplified interface with just chatbot + input field
- Keep existing chat functionality, avatars, feedback, and examples

### 4. Implement Multi-Website Auto-Scraping
**Approach**: Admin interface or API-based registration

**Option A - Admin Panel** (Recommended):
- Keep original `app.py` as admin interface
- Deploy admin interface separately or protect with auth
- Admins can add new websites via UI
- Each scrape creates domain-isolated embeddings

**Option B - Registration API**:
- Add `/api/admin/register-website` endpoint
- POST with URL and domain identifier
- Triggers scraping + embedding workflow
- Returns widget embed code with domain parameter

**Environment Variables**:
```
INTERNAL_API_URL=http://localhost:8000  # Internal backend
PUBLIC_GRADIO_URL=https://your-space.hf.space  # For widget
ANTHROPIC_API_KEY=sk-ant-...
MILVUS_HOST=localhost
MILVUS_PORT=19530
```

### 5. Create Embeddable HTML Widget
**File**: `widget/chatbot-widget.html` (new file)

Based on Gradio's official guide, create:

**HTML Structure**:
- Fixed position chat button (bottom-right corner)
- Hidden chat container (slides up when opened)
- Messages display area with scrolling
- Input field + send button
- Close button

**JavaScript Implementation**:
- Import Gradio JS Client from CDN: `@gradio/client`
- Connect to deployed Spaces URL: `Client.connect("https://your-space.hf.space")`
- Extract current domain: `window.location.hostname`
- Send messages with domain filter to backend
- Handle open/close toggle with animations
- Display responses with user/bot styling
- Persist chat history in sessionStorage

**Domain Isolation Logic**:
```javascript
const currentDomain = window.location.hostname;
// Pass to Gradio app which forwards to backend
await client.predict("/chat", {
  message: userMessage,
  domain: currentDomain
});
```

**CSS Customization**:
- Match current dark theme (#252523 background, #C6603F accent)
- Smooth slide-up animation for modal
- Responsive sizing (320px × 500px on mobile, 360px × 600px on desktop)
- Z-index layering to appear above website content
- Shadow and border-radius for modern look

**Widget Features**:
- Persistent across page navigation (optional)
- Unread message indicator
- Typing indicator while bot responds
- Error handling for network issues

### 6. Deploy to Gradio Spaces with Docker
**Files to create/modify**:

**Dockerfile**:
```dockerfile
FROM python:3.11-slim

# Install dependencies for both backend and frontend
COPY backend/requirements.txt /backend/requirements.txt
COPY frontend/requirements.txt /frontend/requirements.txt
RUN pip install -r /backend/requirements.txt -r /frontend/requirements.txt

# Copy application code
COPY backend /backend
COPY frontend /frontend

# Install Milvus standalone
# (Or use external Milvus service)

# Expose ports
EXPOSE 7860 8000

# Start both services using supervisord or simple script
CMD ["sh", "/start.sh"]
```

**start.sh** (Process manager):
```bash
#!/bin/bash
# Start Milvus
milvus-server &

# Start FastAPI backend
cd /backend && uvicorn src.main:app --host 0.0.0.0 --port 8000 &

# Wait for backend to be ready
sleep 5

# Start Gradio frontend
cd /frontend && python app_embed.py
```

**README.md** (Spaces configuration):
```yaml
---
title: Agentic Scraper Widget
emoji: 🤖
colorFrom: orange
colorTo: red
sdk: docker
pinned: false
---
```

**Secrets Configuration** (on Spaces):
- `ANTHROPIC_API_KEY`: Claude API key
- `MILVUS_HOST`: localhost (internal) or external service
- `ADMIN_PASSWORD`: For protecting admin interface (optional)

## Critical Files

### To Create:
1. `frontend/app_embed.py` - Chat-only Gradio interface with domain filtering
2. `widget/chatbot-widget.html` - Embeddable HTML/JS popup widget
3. `widget/README.md` - Widget installation guide
4. `Dockerfile` - Combined backend + frontend deployment
5. `start.sh` - Process manager script to run all services
6. `README_SPACES.md` - Gradio Spaces deployment documentation

### To Modify:
1. `frontend/app.py` - Add admin authentication (optional) or keep as-is for admin use
2. `backend/src/routes/query.py` - Ensure domain filtering works correctly (already implemented at lines 101-102)
3. `backend/src/main.py` - Verify CORS configuration allows widget embedding from any domain

## Implementation Steps

### Step 1: Create Chat-Only Gradio Interface
**File**: `frontend/app_embed.py`

**Actions**:
- Copy `frontend/app.py` to `frontend/app_embed.py`
- Remove all scraping UI components:
  - URL input field (line 344-349)
  - Scrape button (line 350)
  - Scraping progress section (lines 352-355)
  - Embedding progress section (lines 357-359)
  - All scraping event handlers (lines 394-405)
- Modify `chat_fn()` function:
  - Accept a `domain` parameter from Gradio interface
  - Pass `filter_domain=domain` to backend `/api/query/ask` endpoint
  - Update function signature: `async def chat_fn(message: str, history, domain: str)`
- Add domain input (hidden or from query parameter):
  - Option A: Extract from Gradio request headers
  - Option B: Accept as URL query parameter (`?domain=example.com`)
  - Option C: Simple textbox (for testing) that gets hidden in production
- Simplify to just: Title → Chatbot → Message Input → Send Button
- Keep existing features: avatars, feedback, examples, custom CSS theme
- Update launch parameters:
  - Remove `share=True` (Spaces provides permanent URL)
  - Keep `server_port=7860` for Spaces compatibility
  - Set `server_name="0.0.0.0"`

### Step 2: Build HTML Popup Widget
**File**: `widget/chatbot-widget.html`

**Actions**:
- Create standalone HTML file following Gradio's guide structure
- Import Gradio JS Client: `<script type="module" src="https://cdn.jsdelivr.net/npm/@gradio/client/dist/index.min.js"></script>`
- Implement widget HTML structure:
  - Chat toggle button (bottom-right, fixed position)
  - Chat container (modal popup, hidden by default)
  - Header with title and close button
  - Messages container with scrolling
  - Input field and send button
- Add CSS styling:
  - Match dark theme (#252523, #C6603F accent)
  - Smooth animations (slide-up, fade-in)
  - Responsive design (mobile and desktop)
  - High z-index (9999) to appear above content
- Implement JavaScript logic:
  - Connect to Gradio Space on page load
  - Extract domain: `const domain = window.location.hostname`
  - Toggle chat open/close
  - Send messages to Gradio with domain parameter
  - Display messages with user/bot styling
  - Handle errors and show loading states
- Add sessionStorage for chat persistence
- Configuration variable for Spaces URL

**Template**:
```html
<script type="module">
  import { client } from "@gradio/client";

  const app = await client("https://YOUR-SPACE.hf.space");
  const domain = window.location.hostname;

  // Send message with domain
  const result = await app.predict("/chat", {
    message: userMessage,
    domain: domain
  });
</script>
```

### Step 3: Create Docker Deployment Configuration
**Files**: `Dockerfile`, `start.sh`

**Dockerfile Actions**:
- Use `python:3.11-slim` as base image
- Install system dependencies (for Playwright, Milvus)
- Copy and install backend requirements
- Copy and install frontend requirements
- Copy backend and frontend code
- Set up Milvus (or configure external service)
- Expose ports 7860 (Gradio) and 8000 (FastAPI)
- Set CMD to run `start.sh`

**start.sh Actions**:
- Start Milvus service (if bundled)
- Start FastAPI backend on port 8000
- Wait for backend health check
- Start Gradio frontend on port 7860
- Use process manager or simple background processes

### Step 4: Set Up Admin Interface for Website Registration
**Approach**: Keep original `app.py` as admin tool

**Actions**:
- Keep `frontend/app.py` unchanged (full scraping UI)
- Deploy as separate Gradio Space (optional) or protect with auth
- Admins use this to scrape and embed new websites
- Each scrape stores domain metadata in Milvus
- Widget users query via domain filter

**Alternative**: Create API endpoint for programmatic registration
- Add `/api/admin/register` endpoint in backend
- Accept URL and domain identifier
- Trigger scraping and embedding workflow
- Return success status

### Step 5: Deploy to Gradio Spaces
**Actions**:
- Create new Hugging Face Space repository
- Add README with Space metadata (SDK: docker)
- Upload Dockerfile, start.sh, and code
- Configure Spaces secrets:
  - `ANTHROPIC_API_KEY`
  - `MILVUS_HOST` (if using external service)
- Push to Space and monitor build logs
- Test deployed app
- Get permanent Spaces URL

### Step 6: Update Widget with Production URL
**Actions**:
- Update `widget/chatbot-widget.html` with actual Spaces URL
- Test widget on sample website
- Create `widget/README.md` with installation instructions
- Provide simple copy-paste embed code

### Step 7: Documentation and Testing
**Actions**:
- Create `README_SPACES.md` with deployment guide
- Document widget installation process
- Add troubleshooting section
- Test full flow:
  1. Scrape a website via admin interface
  2. Deploy widget to test website
  3. Verify domain isolation (chat only sees scraped content)
  4. Test multiple websites with different domains

## Technical Considerations

### 1. Gradio API Endpoint Access
The Gradio JS Client needs to call a named API endpoint. Current `app.py` uses event handlers, which may not expose a clear API path.

**Solution**: Use Gradio's API mode or create a named function
```python
# Option A: Use gr.Interface with named function
def chat_interface(message, domain):
    # Calls backend with domain filter
    pass

demo = gr.Interface(fn=chat_interface, ...)

# Option B: Use ChatInterface with additional inputs
chatbot = gr.ChatInterface(
    fn=chat_fn,
    additional_inputs=[gr.Textbox(value="", visible=False, label="domain")]
)
```

The JavaScript client will call: `app.predict("/chat", {message: "...", domain: "..."})`

### 2. Domain Extraction and Passing
**Challenge**: How does the Gradio app receive the domain from the widget?

**Solution Options**:
- **Option A (Recommended)**: Widget passes domain as parameter to Gradio API
- **Option B**: Gradio extracts from HTTP Referer header (less reliable)
- **Option C**: Widget includes domain in each message (simple but repetitive)

Implementation in `app_embed.py`:
```python
def chat_fn(message: str, history, domain: str):
    response = await client.post(
        f"{API_URL}/api/query/ask",
        json={
            "question": message,
            "conversation_history": history,
            "filter_domain": domain,  # Filter by domain
            "top_k": 10
        }
    )
```

### 3. Multi-Website Data Isolation
The backend's existing `filter_domain` parameter (query.py:101-102) handles isolation:
- Each scraped website stores its domain in Milvus metadata
- Widget passes `filter_domain=window.location.hostname`
- Vector search only returns chunks matching that domain
- No cross-contamination between websites

**Important**: Ensure domain extraction is consistent:
- During scraping: Domain extracted from URL and stored in Milvus
- During querying: Domain from widget must match stored domain exactly

### 4. Milvus Deployment on Spaces
**Challenge**: Milvus is a heavy service that may not fit Spaces limits

**Solution Options**:
- **Option A**: Use Milvus Lite (standalone, lighter weight)
- **Option B**: Use external managed Milvus service (Zilliz Cloud)
- **Option C**: Switch to simpler vector DB (ChromaDB, FAISS)

**Recommendation**: Start with external Milvus service, then optimize if needed

### 5. Conversation History Management
Current `chat_fn` accepts `conversation_history` parameter. For widget:
- Store chat history in sessionStorage (client-side)
- Pass history with each request
- Gradio app is stateless (no server-side session storage)
- Each widget instance manages its own history

### 6. CORS and Embedding Security
Current CORS configuration (backend/src/main.py):
```python
allow_origins=["*"]  # Already allows all origins
```
This enables embedding on any website. For production:
- Consider restricting to known domains
- Or add API key authentication for widget usage
- Monitor usage and rate limit if needed

## Risks & Mitigations

**Risk 1**: Milvus too resource-intensive for Spaces
- **Mitigation**: Use external managed Milvus service or lighter alternative

**Risk 2**: Widget domain detection fails (localhost, IP addresses)
- **Mitigation**: Add fallback logic, allow manual domain specification

**Risk 3**: Gradio JS Client compatibility issues
- **Mitigation**: Pin @gradio/client version, thoroughly test API calls

**Risk 4**: Widget CSS conflicts with host website
- **Mitigation**: Use unique class prefixes (e.g., `agentscraper-*`), high specificity, consider Shadow DOM

**Risk 5**: Chat history becomes too large
- **Mitigation**: Limit history to last 10 messages, truncate in widget

**Risk 6**: Multiple deployments needed for admin + widget
- **Mitigation**: Combined deployment with routing, or separate Spaces (simpler)

## Success Criteria

1. ✅ Chat-only Gradio app (`app_embed.py`) runs successfully
2. ✅ Domain filtering works correctly (queries isolated by domain)
3. ✅ Widget HTML connects to Gradio Space via JS Client
4. ✅ Widget appears as popup modal in bottom-right corner
5. ✅ Messages send and receive with proper domain filtering
6. ✅ Custom dark theme displays correctly in widget
7. ✅ Multiple websites can be scraped and queried independently
8. ✅ Complete documentation for deployment and widget embedding
9. ✅ Docker deployment runs both backend + frontend on Spaces

## Performance Optimizations (Gradio Best Practices)

Based on Gradio's official performance guide, implement these optimizations in `app_embed.py`:

### 1. Concurrency Configuration
```python
demo = gr.Blocks(...)

# Enable queuing with optimized settings
demo.queue(
    default_concurrency_limit=10,  # Adjust based on Spaces memory
    max_size=50  # Limit queue to prevent excessive wait times
)

# Launch with optimized settings
demo.launch(
    server_port=7860,
    server_name="0.0.0.0",
    max_threads=40  # Default, increase if needed
)
```

**Concurrency Tuning**:
- Start with `default_concurrency_limit=10` for CPU instances
- Increase incrementally while monitoring memory usage
- GPU instances can handle higher concurrency due to faster inference

### 2. Async Functions
Current `chat_fn()` is already async (✅):
```python
async def chat_fn(message: str, history, domain: str):
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Already optimized for concurrent requests
```

### 3. Queue System Benefits
- Gradio uses Server-Sent Events (SSE) to avoid HTTP timeouts
- Essential for long-running RAG queries (60s backend timeout)
- Provides real-time ETA updates to users
- Must enable with `demo.queue()` before launch

### 4. Resource Monitoring
- Monitor Spaces resource usage in HF dashboard
- Consider GPU upgrade if vector search becomes bottleneck
- GPU can provide 10x-50x speedup for embedding operations

### 5. Backend Performance
Current backend already optimized:
- FastAPI async endpoints (✅)
- Milvus vector DB with indexing (✅)
- Claude API streaming (could add)

**Additional optimizations**:
- Cache frequently asked questions (Redis or in-memory)
- Pre-compute embeddings for common queries
- Implement result caching based on domain + query hash

## Next Steps After Implementation

1. **Performance Monitoring**:
   - Track Spaces resource usage (CPU, memory, GPU if applicable)
   - Monitor average response times
   - Adjust `default_concurrency_limit` based on metrics
   - Profile vector search performance

2. **Feature Enhancements**:
   - Add widget customization options (colors, position, size)
   - Implement suggested questions based on website content
   - Add analytics (track popular questions, user satisfaction)
   - Stream responses for better UX (partial answers as they generate)

3. **Admin Tools**:
   - Build UI for managing scraped websites
   - Add re-scraping capability for content updates
   - Implement domain verification before scraping
   - Bulk website import/export

4. **Widget Improvements**:
   - Offline detection and graceful degradation
   - Multi-language support
   - Voice input option
   - Widget preview tool for testing
   - Minimize widget when inactive (reduce screen space)
