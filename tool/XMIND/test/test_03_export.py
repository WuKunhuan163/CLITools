"""Test XMIND export operations (requires active Chrome CDP + open map)."""
import sys
import time
from pathlib import Path

_PROJ = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(_PROJ))
from interface.resolve import setup_paths
setup_paths(str(_PROJ / "tool" / "XMIND" / "main.py"))

import pytest

try:
    from interface.chrome import is_chrome_cdp_available
    CDP_AVAILABLE = is_chrome_cdp_available()
except Exception:
    CDP_AVAILABLE = False


@pytest.mark.skipif(not CDP_AVAILABLE, reason="Chrome CDP not available")
class TestExport:
    def test_export_png_triggers_dialog(self):
        from tool.XMIND.logic.utils.chrome.api import export_map, _ensure_session
        from interface.chrome import real_click
        r = export_map("png")
        assert r.get("ok"), f"export failed: {r}"

        cdp = _ensure_session()
        cancel = cdp.evaluate("""
            (function(){
                var btns = document.querySelectorAll('button');
                for(var b of btns)
                    if(b.textContent.trim()==='Cancel'){
                        var r=b.getBoundingClientRect();
                        return JSON.stringify({x:Math.round(r.x+r.width/2),y:Math.round(r.y+r.height/2)});
                    }
                return null;
            })()
        """)
        if cancel:
            import json
            pos = json.loads(cancel)
            real_click(cdp, pos["x"], pos["y"])
            time.sleep(0.5)

    def test_export_invalid_format(self):
        from tool.XMIND.logic.utils.chrome.api import export_map
        r = export_map("xyz")
        assert not r.get("ok")
        assert "Unknown format" in r.get("error", "")

    def test_zoom_fit(self):
        from tool.XMIND.logic.utils.chrome.api import fit_map
        r = fit_map()
        assert r.get("ok"), f"fit_map failed: {r}"

    def test_zoom_actual(self):
        from tool.XMIND.logic.utils.chrome.api import zoom
        r = zoom("actual")
        assert r.get("ok"), f"zoom actual failed: {r}"


if __name__ == "__main__":
    if not CDP_AVAILABLE:
        print("SKIP: Chrome CDP not available")
        sys.exit(0)
    t = TestExport()
    t.test_export_png_triggers_dialog()
    print("PASS: export_png_triggers_dialog")
    t.test_export_invalid_format()
    print("PASS: export_invalid_format")
    t.test_zoom_fit()
    print("PASS: zoom_fit")
    t.test_zoom_actual()
    print("PASS: zoom_actual")
