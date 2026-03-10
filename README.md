# BioModels RAG — MCP Server for Claude Code

An MCP server that gives Claude Code direct access to the [BioModels](https://www.ebi.ac.uk/biomodels/) biological model database. Search for models by keyword, retrieve them in Antimony format, ask Claude to reason over their structure, and generate Tellurium simulation scripts — all from within Claude Code.

## What it does

Two tools are exposed to Claude:

| Tool | Description |
|---|---|
| `search_biomodels(query)` | Keyword search over ~1000 curated BioModels (name, title, authors, metadata) |
| `get_model_antimony(model_id)` | Download SBML from EBI BioModels and convert to Antimony text |

Claude receives the full Antimony text in its context window and can reason over reactions, species, parameters, and generate simulation code directly.

## Example prompts for Claude Code

Once the MCP is connected, paste any of these into the Claude Code chat:

**Search and explore**
```
Search BioModels for "glycolysis" and summarise which organisms are represented.
```

**Reasoning over model structure** *(from the BioModelsRAG paper, using BIOMD0000000054)*
```
Get the Antimony for BIOMD0000000054.
If I increase the concentration of ions in the reaction between ions and the energy pool,
will the output increase exponentially?
```
```
Get the Antimony for BIOMD0000000054.
What is the identity of the cell compartment in this model?
```
```
Get the Antimony for BIOMD0000000054.
What is the assignment rule for ATP?
```

**Simulation**
```
Get the Antimony for BIOMD0000000054 and write a Tellurium script that
simulates it for 200 hours and plots all species.
```
```
Search for yeast glycolysis models and write a Tellurium simulation for the best one.
```

> **Tip:** To run a Tellurium simulation from Antimony, the basic pattern is:
> ```python
> import tellurium as te
> r = te.loada(antimony_string)
> r.simulate(0, 100, 500)
> r.plot()
> ```
> Claude will generate the full script for you — just ask.

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
git clone https://github.com/DylanEsguerra/BioModelsRAG_MCP.git
cd BioModelsRAG_MCP
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

### 2. Verify the install works

```bash
venv/bin/python3 test_mcp.py
```

Both tools should return results. If this fails, fix it before proceeding.

### 3. Register with Claude Code

```bash
venv/bin/python3 register_mcp.py
```

This script finds your Claude Code config files automatically and adds the server entry with the correct absolute paths for your machine.

**VSCode extension:** After running it, reload the window with `Cmd+Shift+P` → **Developer: Reload Window**, then type `/mcp` in the Claude Code chat — `biomodels-rag` should appear as **Connected**.

**Claude CLI:** Restart your `claude` session.

> **Manual registration:** If the script can't find your config, it will print the exact JSON to paste — follow the instructions it outputs.

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
| `mcp_server.py` | The MCP server — the only file that runs |
| `requirements.txt` | Dependencies: `mcp`, `tellurium`, `requests` |
| `test_mcp.py` | Install verification — run this after `pip install` |
| `register_mcp.py` | Auto-registers the server with Claude Code (VSCode + CLI) |
| `requirements-full-pipeline.txt` | Dependencies for the original BioModelsRAG pipeline (reference only) |
