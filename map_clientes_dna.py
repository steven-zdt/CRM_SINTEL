import sys
import json
from pathlib import Path
sys.path.append(str(Path.cwd()))
from sintel_agent_unified import DNAMapper

try:
    res = DNAMapper.map_app_dna('clientes')
    print(json.dumps(res, indent=2))
except Exception as e:
    print(f"Error: {e}")
