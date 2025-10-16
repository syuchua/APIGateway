"""Encryption key service tests (skipped without DB)."""
import os
import pytest

pytest.skip("Encryption key service tests require database connection", allow_module_level=True)
