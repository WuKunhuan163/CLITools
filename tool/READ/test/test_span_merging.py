import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path("/Applications/AITerminalTools").resolve()
sys.path.append(str(PROJECT_ROOT))

from tool.READ.logic.interface.main import get_span_merger_func

def test_span_merging():
    merge_spans = get_span_merger_func()
    
    # Mock spans with identical styles
    median_size = 12.0
    line_y = 100.0
    
    spans = [
        {"text": "Hello", "flags": 16, "size": 12.0, "font": "Arial-Bold", "origin": (0, 100), "color": 0x231f20},
        {"text": " ", "flags": 16, "size": 12.0, "font": "Arial-Bold", "origin": (30, 100), "color": 0x231f20},
        {"text": "World", "flags": 16, "size": 12.0, "font": "Arial-Bold", "origin": (40, 100), "color": 0x231f20}
    ]
    
    result = merge_spans(spans, median_size, line_y)
    print(f"Test 1 (Identical styles): {result}")
    assert result == "**Hello World**"
    
    # Mock spans with different styles
    spans = [
        {"text": "Part 1", "flags": 16, "size": 12.0, "font": "Arial-Bold", "origin": (0, 100), "color": 0x231f20},
        {"text": " and ", "flags": 0, "size": 12.0, "font": "Arial", "origin": (40, 100), "color": 0x231f20},
        {"text": "Part 2", "flags": 2, "size": 12.0, "font": "Arial-Italic", "origin": (80, 100), "color": 0x231f20}
    ]
    
    result = merge_spans(spans, median_size, line_y)
    print(f"Test 2 (Different styles): {result}")
    assert result == "**Part 1** and *Part 2*"

    # Mock spans with color
    spans = [
        {"text": "Red", "flags": 0, "size": 12.0, "font": "Arial", "origin": (0, 100), "color": 0xFF0000},
        {"text": " Text", "flags": 0, "size": 12.0, "font": "Arial", "origin": (30, 100), "color": 0xFF0000}
    ]
    result = merge_spans(spans, median_size, line_y)
    print(f"Test 3 (Color merging): {result}")
    assert result == '<span style="color:#ff0000">Red Text</span>'

    print("\nAll span merging tests passed!")

if __name__ == "__main__":
    test_span_merging()

