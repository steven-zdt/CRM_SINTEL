"""Smoke tests package for tenant core.

Temporary guard: if heavy native deps (playwright, cryptography) are
missing in the environment, skip collection of these smoke modules to
allow faster unit-test iterations in minimal containers.
"""
import pytest

try:
	import playwright  # type: ignore
	import cryptography  # type: ignore
except Exception:
	pytest.skip("Skipping heavy smoke tests: missing playwright/cryptography in environment", allow_module_level=True)
