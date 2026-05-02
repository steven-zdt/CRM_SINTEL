#!/usr/bin/env python3
"""
Try to compile each .py file; on SyntaxError/IndentationError restore from corresponding .bak if present.
"""
import py_compile
from pathlib import Path

ROOT = Path('.').resolve()
failed = []
restored = []
for p in ROOT.rglob('*.py'):
    if 'venv' in p.parts or 'migrations' in p.parts:
        continue
    try:
        py_compile.compile(str(p), doraise=True)
    except Exception as e:
        failed.append((str(p), str(e)))
        bak = p.with_name(p.name + '.bak')
        if bak.exists():
            p.write_text(bak.read_text(encoding='utf-8'), encoding='utf-8')
            restored.append(str(p))

print('Compile failures:', len(failed))
for f, err in failed[:50]:
    print(' -', f, '->', err.splitlines()[0])

if restored:
    print('\nRestored from backups:')
    for r in restored:
        print(' -', r)
else:
    print('\nNo backups found to restore.')
