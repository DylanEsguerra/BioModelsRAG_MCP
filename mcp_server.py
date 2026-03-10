#!/usr/bin/env python3
"""
BioModelsRAG MCP Server

Exposes two tools to Claude Code:
  - search_biomodels(query)     : keyword search over cached BioModels metadata
  - get_model_antimony(model_id): download SBML and return full Antimony text

Transport: stdio (default for Claude Code MCP integration)
"""

from __future__ import annotations

import contextlib
import io
import os
import tempfile
from typing import Optional

import requests
import tellurium as te
from mcp.server.fastmcp import FastMCP

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

GITHUB_OWNER = "TheBobBob"
GITHUB_REPO_CACHE = "BiomodelsCache"
BIOMODELS_JSON_DB_PATH = "src/cached_biomodels.json"

GITHUB_CACHE_API_URL = (
    f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO_CACHE}"
    f"/contents/{BIOMODELS_JSON_DB_PATH}"
)
BIOMODELS_STORE_RAW = (
    "https://www.ebi.ac.uk/biomodels/model/download/{model_id}"
    "?filename={model_id}_url.xml"
)

# ---------------------------------------------------------------------------
# In-process cache — fetched once per server process lifetime
# ---------------------------------------------------------------------------

_cached_biomodels_data: Optional[dict] = None

# ---------------------------------------------------------------------------
# FastMCP server instance
# ---------------------------------------------------------------------------

mcp = FastMCP("BioModelsRAG")

# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _fetch_biomodels_json() -> dict:
    """Fetch and cache the BioModels metadata JSON from GitHub.

    Uses the GitHub Contents API to get the download URL, then fetches
    the actual JSON. Result is cached for the lifetime of the process.
    """
    global _cached_biomodels_data
    if _cached_biomodels_data is not None:
        return _cached_biomodels_data

    headers = {"Accept": "application/vnd.github+json"}
    response = requests.get(GITHUB_CACHE_API_URL, headers=headers, timeout=30)
    response.raise_for_status()

    metadata = response.json()
    download_url = metadata.get("download_url")
    if not download_url:
        raise ValueError("GitHub API response missing 'download_url'")

    json_response = requests.get(download_url, timeout=30)
    json_response.raise_for_status()

    _cached_biomodels_data = json_response.json()
    return _cached_biomodels_data


# ---------------------------------------------------------------------------
# MCP Tools
# ---------------------------------------------------------------------------


@mcp.tool()
def search_biomodels(query: str) -> str:
    """Search the BioModels database for models matching a keyword query.

    Searches model name, title, authors, and all metadata fields.
    Returns model ID, name, title, authors, and URL for each match.

    Args:
        query: Keyword or phrase to search for (e.g. "glycolysis", "MAPK", "insulin")
    """
    if not query or not query.strip():
        return "Error: query cannot be empty."

    try:
        cached_data = _fetch_biomodels_json()
    except Exception as e:
        return f"Error fetching BioModels cache from GitHub: {e}"

    query_lower = query.strip().lower()
    matches = []

    for model_id, model_data in cached_data.items():
        # Join all field values into one searchable string (mirrors original rag2.py logic)
        model_info = " ".join(str(v).lower() for v in model_data.values())
        if query_lower in model_info:
            matches.append(
                {
                    "id": model_id,
                    "name": model_data.get("name", ""),
                    "title": model_data.get("title", ""),
                    "authors": model_data.get("authors", ""),
                    "url": model_data.get("url", ""),
                }
            )

    if not matches:
        return f"No models found matching query: '{query}'"

    lines = [f"Found {len(matches)} model(s) matching '{query}':\n"]
    for m in matches:
        lines.append(f"ID:      {m['id']}")
        lines.append(f"  Name:    {m['name']}")
        lines.append(f"  Title:   {m['title']}")
        lines.append(f"  Authors: {m['authors']}")
        lines.append(f"  URL:     {m['url']}")
        lines.append("")

    return "\n".join(lines)


@mcp.tool()
def get_model_antimony(model_id: str) -> str:
    """Download the SBML model for a given model ID and convert it to Antimony format.

    Returns the full Antimony text, which Claude can then reason over directly —
    asking questions about reactions, species, parameters, or generating
    Tellurium simulation scripts.

    Args:
        model_id: BioModels ID (e.g. "BIOMD0000000064"). Use search_biomodels first
                  to find a valid ID.
    """
    if not model_id or not model_id.strip():
        return "Error: model_id cannot be empty."

    model_id = model_id.strip()
    sbml_url = BIOMODELS_STORE_RAW.format(model_id=model_id)

    # Step 1: Download SBML XML
    try:
        response = requests.get(sbml_url, timeout=60)
        response.raise_for_status()
    except requests.exceptions.HTTPError:
        if response.status_code == 404:
            return (
                f"Error: Model '{model_id}' not found in EBI BioModels. "
                f"Use search_biomodels to find a valid model ID."
            )
        return f"Error downloading SBML for '{model_id}': HTTP {response.status_code}"
    except requests.exceptions.RequestException as e:
        return f"Error downloading SBML for '{model_id}': {e}"

    # Step 2: Write SBML to a temp file (tellurium requires a file path)
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as tmp_file:
            tmp_file.write(response.content)
            tmp_path = tmp_file.name
    except OSError as e:
        return f"Error writing temporary SBML file: {e}"

    # Step 3: Convert SBML → Antimony via tellurium
    # redirect_stdout suppresses tellurium's debug output, which would
    # corrupt the MCP stdio stream if allowed through.
    try:
        stdout_trap = io.StringIO()
        with contextlib.redirect_stdout(stdout_trap):
            r = te.loadSBMLModel(tmp_path)
            antimony_str = r.getCurrentAntimony()
        return antimony_str
    except Exception as e:
        return f"Error converting SBML to Antimony for '{model_id}': {e}"
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass  # Non-fatal; OS tmp directory will eventually clean up


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()  # Defaults to stdio transport
