#!/usr/bin/env python3
"""
Fix Python files that contain bytes literals with non-ASCII characters.
Converts occurrences like: ("INFO: texto...").encode('utf-8') -> ("INFO: texto...").encode('utf-8')
Also replaces emoji mappings inside the literal before conversion.
"""
import re
from pathlib import Path

ROOT = Path('.').resolve()
EMOJI_MAP = {
    '⚠️': 'WARNING:',
    '✅': 'OK:',
    '❌': 'ERROR:',
    'ℹ️': 'INFO:',
    '🔍': 'INFO:',
}

patterns = [
    re.compile(r"b\"\"\"(.*?)\"\"\"", re.DOTALL),
    re.compile(r"b'''(.*?)'''", re.DOTALL),
    re.compile(r'b"([^"\\]*(?:\\.[^"\\]*)*)"', re.DOTALL),
    re.compile(r"b'([^'\\]*(?:\\.[^'\\]*)*)'", re.DOTALL),
]

modified = []
for p in ROOT.rglob('*.py'):
    if 'venv' in p.parts or 'migrations' in p.parts:
        continue
    text = p.read_text(encoding='utf-8')
    orig = text

    def replace_inner(inner):
        # inner is the raw content captured; unescape common escapes for safety
        s = inner
        # Replace emojis
        for k, v in EMOJI_MAP.items():
            s = s.replace(k, v)
        # If s now contains non-ascii, we'll keep it as unicode string and encode
        if re.search(r"[^\x00-\x7f]", s):
            # Escape backslashes and double quotes
            esc = s.replace('\\', '\\\\').replace('"', '\\"')
            return '("' + esc + '").encode(\'utf-8\')'
        else:
            # If now ASCII-only, just keep as bytes literal but encode to avoid non-ascii
            esc = s.replace('\\', '\\\\').replace('"', '\\"')
            return '("' + esc + '").encode(\'utf-8\')'

    # Apply patterns sequentially
    for pat in patterns:
        def repl(m):
            inner = m.group(1)
            # If inner contains any non-ascii, replace
            if re.search(r"[^\x00-\x7f]", inner):
                return replace_inner(inner)
            return m.group(0)
        text = pat.sub(repl, text)

    if text != orig:
        bak = p.with_name(p.name + '.bak')
        if not bak.exists():
            bak.write_text(orig, encoding='utf-8')
        p.write_text(text, encoding='utf-8')
        modified.append(str(p))

if modified:
    print('Fixed bytes-literal files:')
    for f in modified:
        print(' -', f)
else:
    print('No bytes literals with non-ASCII found')
