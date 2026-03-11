"""
Quick install verification for the biomodels-rag MCP server.
Run this before registering with Claude Code to confirm everything works.

Usage:
    venv/bin/python3 test_mcp.py
"""

import sys
sys.path.insert(0, ".")

from mcp_server import biomodels_search, biomodels_get_antimony

PASS = "PASS"
FAIL = "FAIL"

def test_search():
    result = biomodels_search("glycolysis")
    assert "BIOMD" in result, "Expected at least one BIOMD model ID in search results"
    assert "Found" in result, "Expected result count in output"
    print(f"  [{PASS}] biomodels_search('glycolysis') — returned results")

def test_search_specific():
    result = biomodels_search("BIOMD0000000054")
    assert "Ataullahkhanov" in result, "Expected model name in result"
    print(f"  [{PASS}] biomodels_search('BIOMD0000000054') — found known model")

def test_search_pagination():
    page1 = biomodels_search("glycolysis", limit=5, offset=0)
    page2 = biomodels_search("glycolysis", limit=5, offset=5)
    assert "1–5" in page1, "Expected page 1 range in output"
    assert "6–10" in page2, "Expected page 2 range in output"
    assert page1 != page2, "Expected different results on different pages"
    print(f"  [{PASS}] biomodels_search pagination — limit and offset work correctly")

def test_get_antimony():
    result = biomodels_get_antimony("BIOMD0000000054")
    assert result.startswith("//"), f"Expected Antimony comment header, got: {result[:80]}"
    assert "U2: 3 I + E =>" in result, "Expected ion pump reaction in Antimony"
    print(f"  [{PASS}] biomodels_get_antimony('BIOMD0000000054') — returned valid Antimony")

def test_get_antimony_glycolysis():
    result = biomodels_get_antimony("BIOMD0000000064")
    assert "Teusink" in result or "vGLK" in result, "Expected yeast glycolysis model content"
    print(f"  [{PASS}] biomodels_get_antimony('BIOMD0000000064') — returned yeast glycolysis model")

def test_invalid_model():
    result = biomodels_get_antimony("BIOMD9999999999")
    assert "Error" in result, "Expected error message for invalid model ID"
    print(f"  [{PASS}] biomodels_get_antimony('BIOMD9999999999') — correctly returned error")

def test_tellurium_simulate():
    import tellurium as te
    r = te.loada('S1 -> S2; k1*S1; k1 = 0.1; S1 = 10')
    result = r.simulate(0, 50, 100)
    assert result is not None and len(result) == 100, "Expected 100-row simulation result"
    print(f"  [{PASS}] tellurium simulate — basic simulation works")

if __name__ == "__main__":
    tests = [
        test_search,
        test_search_specific,
        test_search_pagination,
        test_get_antimony,
        test_get_antimony_glycolysis,
        test_invalid_model,
        test_tellurium_simulate,
    ]

    print("biomodels_mcp — install verification\n")
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
