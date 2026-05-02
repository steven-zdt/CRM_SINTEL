"""Utility to remove __pycache__ and .pyc files from the repo.

Run locally or in container to avoid import-file-mismatch issues before tests.
"""
import os
import pathlib

def clean(root='.'):
    root = pathlib.Path(root)
    removed = 0
    for p in root.rglob('__pycache__'):
        try:
            for f in p.iterdir():
                f.unlink()
            p.rmdir()
            removed += 1
        except Exception:
            pass
    for f in root.rglob('*.pyc'):
        try:
            f.unlink()
            removed += 1
        except Exception:
            pass
    print(f"Cleaned {removed} pycache/.pyc items")

if __name__ == '__main__':
    import sys
    root = sys.argv[1] if len(sys.argv) > 1 else '.'
    clean(root)
