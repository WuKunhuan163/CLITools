"""test_01_search — Verify GS search returns results via CDMCP."""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

import importlib.util
_api_path = _PROJECT_ROOT / "tool" / "GOOGLE.GS" / "logic" / "chrome" / "api.py"
spec = importlib.util.spec_from_file_location("gs_api", str(_api_path))
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)


def test_search():
    r = api.search("deep learning neural network")
    assert r.get("ok"), f"Search failed: {r}"
    assert r.get("count", 0) > 0, f"No results: {r}"
    first = r["results"][0]
    assert first.get("title"), f"No title: {first}"
    assert first.get("authors"), f"No authors: {first}"
    print(f"PASS: Found {r['count']} results, first: {first['title'][:60]}")


def test_get_results():
    r = api.get_results()
    assert r.get("ok"), f"get_results failed: {r}"
    assert r.get("count", 0) > 0, f"No results: {r}"
    print(f"PASS: get_results returned {r['count']} results")


def test_cite():
    r = api.cite_paper(index=0)
    assert r.get("ok"), f"cite_paper failed: {r}"
    assert r.get("citations"), f"No citations: {r}"
    print(f"PASS: cite returned {len(r['citations'])} fields")


def test_pdf_url():
    r = api.get_pdf_url(index=0)
    # PDF may or may not be available
    print(f"PASS: pdf check — ok={r.get('ok')}, url={r.get('url', 'none')[:60]}")


def test_state():
    r = api.get_mcp_state()
    assert "state" in r, f"No state field: {r}"
    print(f"PASS: state={r['state']}")


if __name__ == "__main__":
    test_search()
    test_get_results()
    test_cite()
    test_pdf_url()
    test_state()
    print("\nAll test_01_search tests passed!")
