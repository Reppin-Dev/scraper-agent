# CLI Tools

## Overview

Command-line tools for the scraper-agent backend with real-time progress tracking.

## Scrape CLI

A command-line tool for scraping websites with real-time progress tracking.

### Installation

Make sure you have the required dependencies installed:

```bash
pip install -r requirements.txt
```

### Usage

**Basic usage:**
```bash
python -m src.cli.scrape <url>
```

**With options:**
```bash
python -m src.cli.scrape <url> --mode <mode> --purpose "<description>"
```

### Examples

**Scrape a single page:**
```bash
python -m src.cli.scrape https://example.com --mode single-page
```

**Scrape an entire website:**
```bash
python -m src.cli.scrape https://alteaactive.com/winnipeg/faq/ --mode whole-site --purpose "Scrape gym FAQ and information"
```

**Custom API endpoint:**
```bash
python -m src.cli.scrape https://example.com --api-url http://localhost:8000
```

**Adjust polling interval:**
```bash
python -m src.cli.scrape https://example.com --poll-interval 0.5
```

### Options

- `url` (required): The URL to scrape
- `--mode`: Scrape mode - either "single-page" or "whole-site" (default: "whole-site")
- `--purpose`: Description of what you're scraping for (default: "General web scraping")
- `--api-url`: API base URL (default: "http://localhost:8000")
- `--poll-interval`: How often to poll for status updates in seconds (default: 1.0)

### Output

The CLI provides real-time updates with:
- **Spinner animation** while scraping is in progress
- **Page count** showing how many pages have been scraped
- **Elapsed time** tracking
- **Status updates** (pending → in progress → completed/failed)
- **Final summary** with:
  - Total pages scraped
  - Duration
  - List of scraped URLs
  - Session ID for future reference

### Example Session

```bash
$ python -m src.cli.scrape https://alteaactive.com/winnipeg/faq/

Starting scrape of: https://alteaactive.com/winnipeg/faq/

Session created: 20251126_143052_abc123

⠋ Scraping... 15 pages scraped [00:23]

╭─────────── Scrape Complete ───────────╮
│ Status         COMPLETED              │
│ URL            https://alteaactive... │
│ Mode           whole-site             │
│ Pages Scraped  27                     │
│ Elapsed Time   45.3s                  │
╰───────────────────────────────────────╯

Scraped 27 URLs:
  1. https://alteaactive.com/winnipeg/faq/
  2. https://alteaactive.com/winnipeg/pricing/
  3. https://alteaactive.com/winnipeg/schedule/
  ... and 24 more

Session ID: 20251126_143052_abc123
```

### Help

For more information, use the `--help` flag:

```bash
python -m src.cli.scrape --help
```

---

## Embed Sites CLI

A command-line tool for embedding scraped website content into Milvus vector database with real-time progress tracking.

### Installation

Make sure you have the required dependencies installed and Milvus running:

```bash
pip install -r requirements.txt
```

### Commands

The embed CLI has three main commands: `list`, `embed`, and `delete`.

#### List Command

List all available cleaned markdown files ready for embedding.

```bash
python -m src.cli.embed_sites list
```

**Example output:**
```
Available Cleaned Markdown Files (1)
┏━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━┳━━━━━━━┓
┃ # ┃ Filename                               ┃ Gym/Site        ┃ Pages ┃
┡━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━╇━━━━━━━┩
│ 1 │ fitfactoryfitness.com__20251125.json   │ FitFactory      │    56 │
└───┴────────────────────────────────────────┴─────────────────┴───────┘
```

#### Embed Command

Embed cleaned markdown files into Milvus with multi-level progress tracking.

**Embed all files:**
```bash
python -m src.cli.embed_sites embed
```

**Embed a specific file:**
```bash
python -m src.cli.embed_sites embed --file fitfactoryfitness.com__20251125_155930.json
```

**Recreate collection and embed:**
```bash
python -m src.cli.embed_sites embed --recreate
```

**Options:**
- `--file`: Specific file to embed (optional)
- `--recreate`: Drop existing collection and recreate before embedding (optional flag)

**Progress Display:**

The embed command shows three levels of real-time progress:
- **Files Progress**: Overall file processing (e.g., 1/1 files)
- **Pages Progress**: Pages within current file (e.g., 56/56 pages)
- **Chunks Progress**: Text chunks being embedded (e.g., 1/1 chunks)

**Example output:**
```
Loading BGE-M3 embedding model...
✓ Model loaded successfully

Processing fitfactoryfitness.com__20251125.json... ━━━━━━━ 100% (1/1)
  Pages:                                            ━━━━━━━ 100% (56/56)
  Chunks:                                           ━━━━━━━ 100% (1/1)

╭───────────────────── Embedding Complete ──────────────────────╮
│   Files Processed    1/1                                      │
│   Total Chunks       55                                       │
│   Duration           12.5s                                    │
│   Status             All files embedded successfully          │
╰───────────────────────────────────────────────────────────────╯
```

#### Delete Command

Delete the Milvus collection or specific domain data with confirmation prompts.

**Delete entire collection (with confirmation):**
```bash
python -m src.cli.embed_sites delete
```

**Delete entire collection (skip confirmation):**
```bash
python -m src.cli.embed_sites delete --force
```

**Delete specific domain (with confirmation):**
```bash
python -m src.cli.embed_sites delete --domain fitfactoryfitness.com
```

**Delete specific domain (skip confirmation):**
```bash
python -m src.cli.embed_sites delete --domain fitfactoryfitness.com --force
```

**Options:**
- `--domain`: Delete only data for a specific domain (optional)
- `--force`: Skip confirmation prompt (optional flag)

**Example output:**
```bash
$ python -m src.cli.embed_sites delete

Are you sure you want to delete the entire collection 'gym_sites'? [y/N]: y
Deleting collection: gym_sites
✓ Collection 'gym_sites' deleted successfully
```

### Workflow Example

Here's a typical workflow using all three commands:

```bash
# 1. Check what files are available
python -m src.cli.embed_sites list

# 2. Embed all files into Milvus
python -m src.cli.embed_sites embed

# 3. If you need to re-embed, delete and recreate
python -m src.cli.embed_sites delete --force
python -m src.cli.embed_sites embed

# Or use the --recreate flag
python -m src.cli.embed_sites embed --recreate
```

### Technical Details

- **Embedding Model**: BGE-M3 (BAAI/bge-m3) with 1024-dimensional dense vectors
- **Vector Database**: Milvus with HNSW index for fast similarity search
- **Chunking Strategy**: Markdown-aware chunking with 4000 character max per chunk
- **Progress Tracking**: Real-time progress bars using Rich library
- **Safety Features**: Confirmation prompts for destructive operations (unless `--force` is used)
