import sys
sys.path.insert(0, '/Applications/AITerminalTools')
sys.path.insert(0, '/Applications/AITerminalTools/tool/GOOGLE.CDMCP')
from logic.resolve import setup_paths
setup_paths('/Applications/AITerminalTools')
import importlib.util
spec = importlib.util.spec_from_file_location('demo', '/Applications/AITerminalTools/tool/GOOGLE.CDMCP/logic/cdp/demo.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
mod.run_demo_on_tab('ws://localhost:9222/devtools/page/ED74C4607CDBBFD97C609FED8C010B77', port=9222)
