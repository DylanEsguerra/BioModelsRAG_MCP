"""
Quick install verification for the biomodels-rag MCP server.
Run this before registering with Claude Code to confirm everything works.

Usage:
    venv/bin/python3 test_mcp.py
"""

import sys
sys.path.insert(0, ".")

from mcp_server import search_biomodels, get_model_antimony

PASS = "PASS"
FAIL = "FAIL"

def test_search():
    result = search_biomodels("glycolysis")
    assert "BIOMD" in result, "Expected at least one BIOMD model ID in search results"
    assert "Found" in result, "Expected result count in output"
    print(f"  [{PASS}] search_biomodels('glycolysis') — returned results")

def test_search_specific():
    result = search_biomodels("BIOMD0000000054")
    assert "Ataullahkhanov" in result, "Expected model name in result"
    print(f"  [{PASS}] search_biomodels('BIOMD0000000054') — found known model")

def test_get_antimony():
    result = get_model_antimony("BIOMD0000000054")
    assert result.startswith("//"), f"Expected Antimony comment header, got: {result[:80]}"
    assert "U2: 3 I + E =>" in result, "Expected ion pump reaction in Antimony"
    print(f"  [{PASS}] get_model_antimony('BIOMD0000000054') — returned valid Antimony")

def test_get_antimony_glycolysis():
    result = get_model_antimony("BIOMD0000000064")
    assert "Teusink" in result or "vGLK" in result, "Expected yeast glycolysis model content"
    print(f"  [{PASS}] get_model_antimony('BIOMD0000000064') — returned yeast glycolysis model")

def test_invalid_model():
    result = get_model_antimony("BIOMD9999999999")
    assert "Error" in result, "Expected error message for invalid model ID"
    print(f"  [{PASS}] get_model_antimony('BIOMD9999999999') — correctly returned error")

if __name__ == "__main__":
    tests = [
        test_search,
        test_search_specific,
        test_get_antimony,
        test_get_antimony_glycolysis,
        test_invalid_model,
    ]

    print("biomodels-rag MCP — install verification\n")
    failures = []
    for test in tests:
        try:
            test()
        except Exception as e:
            print(f"  [{FAIL}] {test.__name__}: {e}")
            failures.append(test.__name__)

    print()
    if failures:
        print(f"FAILED: {len(failures)}/{len(tests)} tests failed: {failures}")
        sys.exit(1)
    else:
        print(f"All {len(tests)} tests passed. Ready to register with Claude Code.")
