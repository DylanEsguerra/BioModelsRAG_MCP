#!/usr/bin/env python3
"""
biomodels_mcp — MCP Server for the BioModels biological model database.

Exposes two tools to Claude Code and Claude Desktop:
  - biomodels_search(query, limit, offset): keyword search over cached BioModels metadata
  - biomodels_get_antimony(model_id):       download SBML and return full Antimony text

Transport: stdio (correct for local single-user integrations per MCP best practices).
Errors and debug output are written to stderr only — never stdout — to avoid
corrupting the MCP stdio stream.
"""

from __future__ import annotations

import contextlib
import io
import os
import sys
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
EBI_SBML_URL = (
    "https://www.ebi.ac.uk/biomodels/model/download/{model_id}"
    "?filename={model_id}_url.xml"
)

# Maximum characters returned by search to avoid overwhelming context windows.
# The guide recommends truncating large responses with a clear message.
SEARCH_CHAR_LIMIT = 20_000

# Default and maximum results per search page
DEFAULT_LIMIT = 20
MAX_LIMIT = 100

# ---------------------------------------------------------------------------
# In-process cache — fetched once per server process lifetime
# ---------------------------------------------------------------------------

_cached_biomodels_data: Optional[dict] = None

# ---------------------------------------------------------------------------
# FastMCP server instance
# Naming follows MCP Python convention: {service}_mcp
# ---------------------------------------------------------------------------

mcp = FastMCP("biomodels_mcp")

# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _log(msg: str) -> None:
    """Write a diagnostic message to stderr (never stdout)."""
    print(f"[biomodels_mcp] {msg}", file=sys.stderr)


def _fetch_biomodels_json() -> dict:
    """Fetch and cache the BioModels metadata JSON from GitHub.

    Uses the GitHub Contents API to get the download URL, then fetches
    the actual JSON. Result is cached for the lifetime of the process.
    """
    global _cached_biomodels_data
    if _cached_biomodels_data is not None:
        return _cached_biomodels_data

    _log("Fetching BioModels metadata cache from GitHub...")
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
    _log(f"Loaded {len(_cached_biomodels_data)} models into cache.")
    return _cached_biomodels_data


# ---------------------------------------------------------------------------
# MCP Tools
# Tool names follow MCP convention: {service}_{action}_{resource}
# ---------------------------------------------------------------------------


@mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": True, "idempotentHint": True})
def biomodels_search(query: str, limit: int = DEFAULT_LIMIT, offset: int = 0) -> str:
    """Search the BioModels database for models matching a keyword query.

    Searches model name, title, authors, and all metadata fields.
    Returns paginated results with model ID, name, title, authors, and URL.

    Args:
        query:  Keyword or phrase to search for (e.g. "glycolysis", "MAPK", "insulin").
        limit:  Maximum number of results to return (1-100, default 20).
        offset: Number of results to skip for pagination (default 0).

    Returns:
        Formatted list of matching models with pagination metadata, or an error string.
        To get the next page, increment offset by limit.
    """
    if not query or not query.strip():
        return "Error: query cannot be empty."
    if not (1 <= limit <= MAX_LIMIT):
        return f"Error: limit must be between 1 and {MAX_LIMIT}."
    if offset < 0:
        return "Error: offset must be 0 or greater."

    try:
        cached_data = _fetch_biomodels_json()
    except Exception as e:
        _log(f"Cache fetch failed: {e}")
        return f"Error fetching BioModels cache from GitHub: {e}"

    query_lower = query.strip().lower()
    all_matches = []

    for model_id, model_data in cached_data.items():
        model_info = " ".join(str(v).lower() for v in model_data.values())
        if query_lower in model_info:
            all_matches.append(
                {
                    "id": model_id,
                    "name": model_data.get("name", ""),
                    "title": model_data.get("title", ""),
                    "authors": model_data.get("authors", ""),
                    "url": model_data.get("url", ""),
                }
            )

    total = len(all_matches)
    if total == 0:
        return f"No models found matching query: '{query}'"

    page = all_matches[offset : offset + limit]
    has_more = total > offset + len(page)
    next_offset = offset + len(page) if has_more else None

    lines = [
        f"Found {total} model(s) matching '{query}' "
        f"(showing {offset + 1}–{offset + len(page)} of {total}):"
    ]
    if has_more:
        lines.append(f"  → Use offset={next_offset} to get the next page.\n")
    else:
        lines.append("")

    for m in page:
        lines.append(f"ID:      {m['id']}")
        lines.append(f"  Name:    {m['name']}")
        lines.append(f"  Title:   {m['title']}")
        lines.append(f"  Authors: {m['authors']}")
        lines.append(f"  URL:     {m['url']}")
        lines.append("")

    result = "\n".join(lines)

    # Truncate if response is very large (e.g. broad queries like "model")
    if len(result) > SEARCH_CHAR_LIMIT:
        result = result[:SEARCH_CHAR_LIMIT]
        result += (
            f"\n\n[Response truncated at {SEARCH_CHAR_LIMIT} characters. "
            f"Use a more specific query or increase offset to page through results.]"
        )

    return result


@mcp.tool(annotations={"readOnlyHint": True, "openWorldHint": True, "idempotentHint": True})
def biomodels_get_antimony(model_id: str) -> str:
    """Download the SBML model for a given BioModels ID and convert it to Antimony format.

    Returns the full Antimony text, which Claude can then reason over directly —
    asking questions about reactions, species, parameters, or generating
    Tellurium simulation scripts.

    To simulate a model with Tellurium after retrieving the Antimony, use this pattern:

        import tellurium as te
        r = te.loada(antimony_string)
        r.simulate(0, 100, 500)
        r.plot()

    For SBML-based loading (if loada fails due to boundary species):

        import tellurium as te, requests, tempfile, os
        url = f"https://www.ebi.ac.uk/biomodels/model/download/{model_id}?filename={model_id}_url.xml"
        r = requests.get(url); tmp = tempfile.mktemp(suffix=".xml")
        open(tmp, "wb").write(r.content)
        model = te.loadSBMLModel(tmp); model.simulate(0, 100, 500); model.plot()
        os.unlink(tmp)

    Args:
        model_id: BioModels ID (e.g. "BIOMD0000000064"). Use biomodels_search first
                  to find a valid ID.

    Returns:
        Full Antimony text of the model, or an error string if the model is not found
        or cannot be converted.
    """
    if not model_id or not model_id.strip():
        return "Error: model_id cannot be empty."

    model_id = model_id.strip()
    sbml_url = EBI_SBML_URL.format(model_id=model_id)
    _log(f"Downloading SBML for {model_id}...")

    # Step 1: Download SBML XML
    try:
        response = requests.get(sbml_url, timeout=60)
        response.raise_for_status()
    except requests.exceptions.HTTPError:
        if response.status_code == 404:
            return (
                f"Error: Model '{model_id}' not found in EBI BioModels. "
                f"Use biomodels_search to find a valid model ID."
            )
        return f"Error downloading SBML for '{model_id}': HTTP {response.status_code}"
    except requests.exceptions.RequestException as e:
        _log(f"SBML download failed: {e}")
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
    # Redirect stdout to suppress tellurium debug output — it must never reach
    # the MCP stdio stream or it will corrupt the JSON-RPC framing.
    try:
        stdout_trap = io.StringIO()
        with contextlib.redirect_stdout(stdout_trap):
            r = te.loadSBMLModel(tmp_path)
            antimony_str = r.getCurrentAntimony()
        _log(f"Successfully converted {model_id} to Antimony ({len(antimony_str)} chars).")
        return antimony_str
    except Exception as e:
        _log(f"Antimony conversion failed: {e}")
        return f"Error converting SBML to Antimony for '{model_id}': {e}"
    finally:
        if tmp_path:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass  # Non-fatal; OS will eventually clean up tmp directory


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()  # Defaults to stdio transport
