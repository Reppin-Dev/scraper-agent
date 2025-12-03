# Claude API Usage in Agentic Scraper

## Overview

The Agentic Scraper uses the Claude API at 4 critical stages of the web scraping and question-answering pipeline. This document explains how each Claude model is used, which tools are leveraged, and the strategic reasoning behind model selection.

---

## Table of Contents

- [1. RAG Q&A Pipeline](#1-rag-qa-pipeline)
- [2. Schema Generation](#2-schema-generation)
- [3. Content Extraction](#3-content-extraction)
- [4. Web Search for Missing Data](#4-web-search-for-missing-data)
- [Model Selection Strategy](#model-selection-strategy)
- [Claude API Tools](#claude-api-tools)
- [Complete Pipeline Flow](#complete-pipeline-flow)
- [Cost Optimization](#cost-optimization)

---

## 1. RAG Q&A Pipeline

**Location**: `src/routes/query.py`

This is the core user-facing feature - a 3-stage Retrieval-Augmented Generation (RAG) system.

### Stage 1: Query Rewriting with Claude Haiku

**Purpose**: Optimize user questions into better search queries for vector database retrieval.

```python
client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

query_message = client.messages.create(
    model="claude-3-5-haiku-20241022",  # Fast, cheap model for simple task
    max_tokens=100,
    messages=[{"role": "user", "content": query_rewrite_prompt}]
)

optimized_query = query_message.content[0].text.strip()
```

**Example**:
- **Input**: "What services does this business offer?"
- **Output**: "business services offerings products"

**Why Claude Haiku?**
- Fast response time (~1 second)
- Low cost (~$0.25 per million input tokens)
- Perfect for simple text transformation tasks

### Stage 2: Vector Search

No Claude API used here. Uses:
- **BGE-M3 embeddings** (local model)
- **Milvus vector database** for similarity search

### Stage 3: Answer Synthesis with Claude Sonnet

**Purpose**: Generate comprehensive, natural language answers from retrieved context.

```python
answer_message = client.messages.create(
    model="claude-sonnet-4-20250514",  # Most capable model
    max_tokens=1024,
    system=system_prompt,
    messages=[{"role": "user", "content": user_prompt}]
)

answer = answer_message.content[0].text
```

**Input**:
- User's original question
- Retrieved text chunks from vector database (5-10 sources)
- System prompt with guidelines

**Output**:
- Detailed, well-structured answer
- Organized information from multiple sources
- Natural language response with specific details

**Example from Production**:
```
Question: "What services does this business offer?"

Context: 5 chunks from heartlakecleaners.com

Answer: "Based on the information provided, Heartlake Cleaners offers
several key services:

## Main Services:

**Cleaning Services:**
- Full service laundry and wet cleaning
- Wash and fold service
- Dry cleaning (using eco-friendly methods)
[... detailed breakdown continues ...]"
```

**Why Claude Sonnet 4?**
- Best-in-class reasoning and synthesis capabilities
- Excellent at organizing information from multiple sources
- Strong instruction following for citation requirements
- High-quality natural language generation

---

## 2. Schema Generation

**Location**: `src/agents/base/base_schema_generator.py`

**Purpose**: Automatically generate JSON extraction schemas by analyzing website structure.

### Method A: From URL (with Web Fetch Tool)

```python
message = self.client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=2048,
    messages=[{"role": "user", "content": prompt}],
    tools=[{
        "type": "web_fetch_20250910",
        "name": "web_fetch",
        "max_uses": 3
    }],
    extra_headers={"anthropic-beta": "web-fetch-2025-09-10"}
)
```

**How it works**:
1. Claude autonomously fetches the URL using the `web_fetch` tool
2. Analyzes HTML structure, content patterns, and data types
3. Generates a JSON schema defining what fields to extract

**Example Output**:
```json
{
  "business_name": {
    "type": "string",
    "description": "Official name of the business"
  },
  "services": {
    "type": "array",
    "items": {"type": "string"},
    "description": "List of services offered"
  },
  "pricing": {
    "type": "object",
    "description": "Service pricing information"
  },
  "hours_of_operation": {
    "type": "string",
    "description": "Business hours"
  }
}
```

### Method B: From HTML Sample

```python
message = self.client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=2048,
    messages=[{"role": "user", "content": prompt}]
)
```

**Use case**: When HTML is already scraped locally via Playwright.

**Why Claude Sonnet 4?**
- Deep understanding of HTML structure
- Ability to infer appropriate data types
- Creates semantic, meaningful field names
- Handles complex nested structures

---

## 3. Content Extraction

**Location**: `src/agents/base/base_content_extractor.py`

**Purpose**: Extract structured JSON data from webpages using a predefined schema.

### Method A: URL-based Extraction (with Web Fetch)

```python
message = self.client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=4096,
    messages=[{"role": "user", "content": prompt}],
    tools=[{
        "type": "web_fetch_20250910",
        "name": "web_fetch",
        "max_uses": 3
    }],
    extra_headers={"anthropic-beta": "web-fetch-2025-09-10"}
)
```

**Flow**:
1. Receive extraction schema (from schema generator)
2. Claude fetches URL autonomously
3. Parses HTML according to schema
4. Returns structured JSON data

### Method B: HTML-based Extraction

```python
message = self.client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=4096,
    messages=[{"role": "user", "content": prompt}]
)
```

**Flow**:
1. HTML already scraped via Playwright
2. Claude extracts specific fields from HTML
3. Returns JSON matching the schema

**Example**:

**Schema**:
```json
{
  "name": "string - Business name",
  "services": "array of strings"
}
```

**HTML Input**: Full webpage HTML

**Output**:
```json
{
  "name": "Heartlake Cleaners",
  "services": [
    "Dry Cleaning",
    "Wet Cleaning",
    "Alterations",
    "Wash and Fold"
  ]
}
```

**Why Claude Sonnet 4?**
- Precise data extraction from complex HTML
- Handles edge cases (missing fields, varied formats)
- Strong JSON output formatting
- Reliable parsing of semi-structured content

---

## 4. Web Search for Missing Data

**Location**: `src/services/web_search.py`

**Purpose**: Fill in missing fields (Google Maps links, hours of operation) using web search.

```python
message = self.client.messages.create(
    model="claude-sonnet-4-5-20250929",  # Latest Sonnet with enhanced web search
    max_tokens=2048,
    messages=[{"role": "user", "content": prompt}],
    tools=[{
        "type": "web_search_20250305",
        "name": "web_search",
        "max_uses": 5
    }]
)
```

**How it works**:
1. After initial scraping, system identifies missing required fields
2. Claude uses `web_search` tool to autonomously search Google
3. Extracts specific missing data from search results
4. Returns only the requested fields

**Example**:

**Input**:
```
Find Google Maps link and hours for "Heartlake Cleaners" in Brampton, Ontario
```

**Claude's Actions**:
- Searches: "Heartlake Cleaners Brampton Google Maps"
- Searches: "Heartlake Cleaners hours of operation"
- Parses results

**Output**:
```json
{
  "google_maps_link": "https://maps.google.com/maps?cid=12345...",
  "hours_of_operation": "Mon-Fri: 7am-7pm, Sat: 8am-5pm, Sun: Closed"
}
```

**Why Claude Sonnet 4.5?**
- Latest model with improved web search capabilities
- Better at interpreting search results
- More reliable extraction from varied web sources

---

## Model Selection Strategy

| **Task** | **Model** | **Input Tokens** | **Output Tokens** | **Why This Model** |
|----------|-----------|------------------|-------------------|--------------------|
| Query Rewriting | Claude 3.5 Haiku | ~50 | ~20 | Fast, cheap, simple text transformation |
| Answer Synthesis | Claude Sonnet 4 | ~5,000 | ~1,024 | Best quality for complex reasoning |
| Schema Generation | Claude Sonnet 4 | ~2,000 | ~2,048 | Deep HTML understanding required |
| Content Extraction | Claude Sonnet 4 | ~3,000 | ~4,096 | Precise data parsing from complex HTML |
| Web Search | Claude Sonnet 4.5 | ~1,000 | ~2,048 | Latest with enhanced web search |

### Cost Comparison

**Query Rewriting (Haiku)**:
- Input: $0.25/M tokens
- Output: $1.25/M tokens
- Cost per query: ~$0.00003

**Answer Synthesis (Sonnet 4)**:
- Input: $3/M tokens
- Output: $15/M tokens
- Cost per query: ~$0.03

**Using Haiku for rewriting saves ~90% on that step vs using Sonnet!**

---

## Claude API Tools

### 1. Web Fetch Tool (`web_fetch_20250910`)

**Capabilities**:
- Autonomously browse URLs
- Handle JavaScript-rendered content
- Follow redirects
- Extract clean text from HTML

**Configuration**:
```python
tools=[{
    "type": "web_fetch_20250910",
    "name": "web_fetch",
    "max_uses": 3  # Can make up to 3 fetches per request
}]

# Requires beta header:
extra_headers={"anthropic-beta": "web-fetch-2025-09-10"}
```

**Used in**:
- Schema Generation (from URL)
- Content Extraction (from URL)

**Benefits**:
- No need for external scraping libraries for simple pages
- Claude handles parsing and extraction in one step
- Reduces code complexity

### 2. Web Search Tool (`web_search_20250305`)

**Capabilities**:
- Search Google for information
- Parse search results
- Extract specific data points
- Follow multiple search queries

**Configuration**:
```python
tools=[{
    "type": "web_search_20250305",
    "name": "web_search",
    "max_uses": 5  # Can perform up to 5 searches
}]
```

**Used in**:
- Finding missing gym/business data
- Google Maps links
- Hours of operation

**Benefits**:
- Automated data enrichment
- No manual API integrations needed
- Claude intelligently refines searches

---

## Complete Pipeline Flow

### Example: Full User Journey

**Scenario**: User scrapes a dry cleaning business website and asks questions

#### Step 1: Scraping (No Claude)
- **Tool**: Playwright browser automation
- **Process**: Crawls website, extracts HTML
- **Output**: Raw HTML stored in sessions

#### Step 2: HTML Cleaning (No Claude)
- **Tool**: HTML Cleaner service
- **Process**: Convert HTML → Clean Markdown
- **Output**: `cleaned_markdown/heartlakecleaners.com__[session_id].json`

#### Step 3: Embedding (No Claude)
- **Tool**: BGE-M3 model (local)
- **Process**: Generate 1024-dim vectors
- **Output**: Embeddings stored in Milvus

#### Step 4: User Asks Question
**User Input**: "What services does this business offer?"

#### Step 5: Query Rewriting (Claude Haiku)
- **Model**: claude-3-5-haiku-20241022
- **Input**: "What services does this business offer?"
- **Process**: Extract keywords and concepts
- **Output**: "business services offerings products"

#### Step 6: Vector Search (No Claude)
- **Tool**: Milvus vector database
- **Process**: Cosine similarity search
- **Output**: Top 5-10 most relevant text chunks

#### Step 7: Answer Synthesis (Claude Sonnet 4)
- **Model**: claude-sonnet-4-20250514
- **Input**:
  - Original question
  - Retrieved chunks (5-10 sources)
- **Process**: Synthesize comprehensive answer
- **Output**:
```
Based on the information provided, Heartlake Cleaners offers:

## Main Services:
- Full service laundry and wet cleaning
- Wash and fold service
- Professional dry cleaning (eco-friendly)
- Alterations and tailoring

[... detailed answer continues ...]
```

**Total Latency**: ~3-5 seconds
**Total Cost**: ~$0.03-0.05 per Q&A interaction

---

## Cost Optimization Strategies

### 1. Strategic Model Selection
✅ **Current**: Haiku for rewriting, Sonnet for synthesis
❌ **Alternative**: Sonnet for both
💰 **Savings**: ~90% on rewriting step

### 2. Local Embeddings
✅ **Current**: BGE-M3 runs locally
❌ **Alternative**: Claude embeddings API
💰 **Savings**: 100% (no API cost for embeddings)

### 3. Efficient Context Management
✅ **Current**: Only send top-k relevant chunks
❌ **Alternative**: Send entire document
💰 **Savings**: ~80% reduction in input tokens

### 4. Prompt Caching (Future Enhancement)

**Potential implementation**:
```python
# Cache the system prompt across requests
answer_message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1024,
    system=[{
        "type": "text",
        "text": system_prompt,
        "cache_control": {"type": "ephemeral"}
    }],
    messages=[{"role": "user", "content": user_prompt}]
)
```

**Potential Savings**: 90% off cached tokens (system prompts in RAG)

---

## API Key Configuration

All Claude API calls use a single API key from environment variables:

**Configuration** (`src/config/settings.py`):
```python
import os
from dotenv import load_dotenv

load_dotenv()

anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
```

**Usage across all modules**:
```python
from anthropic import Anthropic
from ..config import settings

client = Anthropic(api_key=settings.anthropic_api_key)
```

**Environment Setup** (`.env`):
```bash
ANTHROPIC_API_KEY=sk-ant-api03-...
```

---

## Error Handling

All Claude API calls include error handling:

```python
try:
    message = client.messages.create(...)

    # Extract response
    response_text = ""
    for block in message.content:
        if hasattr(block, 'text') and block.text:
            response_text += block.text

except Exception as e:
    logger.error(f"Claude API error: {e}")
    return {}, f"Error: {str(e)}"
```

**Common error scenarios**:
- API rate limits
- Invalid API key
- Network timeouts
- Malformed JSON responses

---

## Future Enhancements

### 1. Prompt Caching
- Cache system prompts in RAG pipeline
- Reduce costs by 90% on repeated queries

### 2. Batch Processing
- Process multiple URLs in parallel
- Reduce latency for bulk operations

### 3. Streaming Responses
```python
with client.messages.stream(
    model="claude-sonnet-4-20250514",
    messages=[...]
) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)
```

Benefits:
- Better UX with progressive loading
- Lower perceived latency

### 4. Extended Context
- Upgrade to Claude Sonnet 4 with 200K context
- Process entire websites in single request
- Eliminate chunking for small sites

---

## Summary

### Claude Powers 4 Core Features:

1. **Smart Q&A**
   - 2-stage RAG with query optimization + synthesis
   - Haiku → Vector Search → Sonnet

2. **Auto Schema Generation**
   - Analyzes websites to create extraction schemas
   - Uses web_fetch tool for autonomous browsing

3. **Intelligent Extraction**
   - Parses HTML into structured JSON
   - Handles complex, semi-structured content

4. **Data Enrichment**
   - Fills missing fields via web search
   - Autonomously searches Google for specific data

### 3 Models Used Strategically:

- **Claude 3.5 Haiku**: Fast/cheap query rewriting (~$0.00003/query)
- **Claude Sonnet 4**: High-quality extraction & synthesis (~$0.03/query)
- **Claude Sonnet 4.5**: Enhanced web search capabilities

### 2 Specialized Tools:

- **web_fetch**: Autonomous URL browsing and content extraction
- **web_search**: Google search integration for data enrichment

**Result**: A fully autonomous web scraping and Q&A system powered by Claude's advanced reasoning and tool-use capabilities.
