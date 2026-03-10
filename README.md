# BioModels RAG — MCP Server for Claude Code

An MCP server that gives Claude Code direct access to the [BioModels](https://www.ebi.ac.uk/biomodels/) biological model database. Search for models by keyword, retrieve them in Antimony format, ask Claude to reason over their structure, and generate Tellurium simulation scripts — all from within Claude Code.

## What it does

Two tools are exposed to Claude:

| Tool | Description |
|---|---|
| `search_biomodels(query)` | Keyword search over ~1000 curated BioModels (name, title, authors, metadata) |
| `get_model_antimony(model_id)` | Download SBML from EBI BioModels and convert to Antimony text |

Claude receives the full Antimony text in its context window and can reason over reactions, species, parameters, and generate simulation code directly.

## Example workflow in Claude Code

```
Search biomodels for "glycolysis" and get the Antimony for one of them.
Write a Tellurium simulation script and run it.
```

```
If I increase the ion concentration in BIOMD0000000054, will ATP increase exponentially?
```

## Architecture

```
Claude Code
    │
    │  stdio (MCP protocol)
    ▼
mcp_server.py  (FastMCP)
    │
    ├── search_biomodels()  ──► GitHub: TheBobBob/BiomodelsCache (JSON metadata)
    │
    └── get_model_antimony() ─► EBI BioModels REST API (SBML XML)
                                    │
                                    └── tellurium.loadSBMLModel()
                                              │
                                              └── Antimony text → Claude's context
```

## Setup

### Prerequisites

- Python 3.10+
- Claude Code (VSCode extension or CLI)

> **Note:** No `.claude/settings.local.json` is included in this repo — Claude Code will create one automatically with your own paths when you first use it in this directory. You do not need to create or configure it manually.

### 1. Clone and install

```bash
git clone https://github.com/YOUR_USERNAME/AntimonyRAG_Agent.git
cd AntimonyRAG_Agent
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

### 2. Verify the install works

```bash
venv/bin/python3 test_mcp.py
```

Both tools should return results. If this fails, fix it before proceeding.

### 3. Register with Claude Code

**There are two registration methods depending on how you run Claude Code.**

#### Option A: VSCode Extension (recommended)

Edit `~/.claude.json` (your home directory — note: **not** `~/.claude/claude.json`) and add the `mcpServers` key:

```json
{
  "mcpServers": {
    "biomodels-rag": {
      "type": "stdio",
      "command": "/absolute/path/to/AntimonyRAG_Agent/venv/bin/python3",
      "args": ["/absolute/path/to/AntimonyRAG_Agent/mcp_server.py"]
    }
  }
}
```

Then reload the VSCode window: `Cmd+Shift+P` → **Developer: Reload Window**.

Verify it connected: type `/mcp` in the Claude Code chat — `biomodels-rag` should appear as **Connected**.

#### Option B: Claude Code CLI

```bash
claude mcp add --transport stdio biomodels-rag -- \
  /absolute/path/to/AntimonyRAG_Agent/venv/bin/python3 \
  /absolute/path/to/AntimonyRAG_Agent/mcp_server.py
```

Then restart the `claude` CLI session.

> **Note:** The CLI writes to `~/.claude/claude.json`, which is a different file from `~/.claude.json` used by the VSCode extension. Each method only works for its respective client.

## Design notes

**Why no Ollama / ChromaDB?**
The original BioModelsRAG pipeline summarized each model chunk with a local LLM, stored embeddings in ChromaDB, and used semantic search before querying. This MCP skips all of that — the full Antimony text is returned directly into Claude's context. Claude's context window easily fits the raw model text, and reasoning over the actual model text is higher fidelity than reasoning over summaries.

**Why stdio transport?**
Zero configuration — no port, no daemon, no firewall rules. Claude Code launches the server as a child process.

**SBML source**
Models are downloaded from the EBI BioModels REST API:
```
https://www.ebi.ac.uk/biomodels/model/download/{model_id}?filename={model_id}_url.xml
```

## Files

| File | Purpose |
|---|---|
| `mcp_server.py` | The MCP server — the primary deliverable |
| `requirements.txt` | Minimal dependencies for the MCP server (`mcp`, `tellurium`, `requests`) |
| `test_mcp.py` | Quick install verification script |
| `requirements-full-pipeline.txt` | Dependencies for the original BioModelsRAG pipeline (reference only) |
| `simulate_BIOMD0000000054.py` | Example Tellurium simulation (erythrocyte adenylate model) |
| `simulate_BIOMD0000000064.py` | Example Tellurium simulation (yeast glycolysis, Teusink 2000) |
| `BioModelsRAG/` | Original pipeline code (reference only, not used by MCP) |
