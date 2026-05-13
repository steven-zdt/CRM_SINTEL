import importlib
import json
import os
import py_compile
import subprocess
import sys
from pathlib import Path

TARGET_APP = ""
if len(sys.argv) > 1:
    TARGET_APP = sys.argv[1].strip()
else:
    TARGET_APP = os.getenv("SINTEL_APP_NAME", "").strip()

OUT = {"py_compile": None, "auditor": None, "ruff": None, "target_app": TARGET_APP or "all"}

# 1) py_compile
try:
    py_compile.compile(str(Path('sintel_agent_unified.py')), doraise=True)
    OUT['py_compile'] = 'ok'
except Exception as e:
    OUT['py_compile'] = {'error': str(e)}

# 2) import and run auditor
try:
    # ensure workspace root is on sys.path so imports from project root work when
    # executing this script from the `tools/` directory
    sys.path.insert(0, str(Path.cwd()))
    if 'sintel_agent_unified' in sys.modules:
        importlib.reload(sys.modules['sintel_agent_unified'])
    import sintel_agent_unified as sau
    if TARGET_APP:
        report = sau.Tools.expert_e2e_auditor(TARGET_APP)
    else:
        apps = sau.Tools.list_apps().get("tenant_apps", [])
        report = {
            "mode": "all_apps",
            "apps_count": len(apps),
            "apps": [
                sau.Tools.expert_e2e_auditor(app)
                for app in apps
                if app not in ("api", "core")
            ],
        }
    OUT['auditor'] = report
except Exception as e:
    OUT['auditor'] = {'error': str(e)}

# 3) ruff check
try:
    proc = subprocess.run([sys.executable, '-m', 'ruff', 'check', 'sintel_agent_unified.py'], capture_output=True, text=True, timeout=120)
    OUT['ruff'] = {'returncode': proc.returncode, 'stdout': proc.stdout, 'stderr': proc.stderr}
except Exception as e:
    OUT['ruff'] = {'error': str(e)}

print(json.dumps(OUT))
