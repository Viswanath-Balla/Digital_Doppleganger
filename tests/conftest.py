"""Shared test fixtures."""

from __future__ import annotations

import os
import sys

# Ensure project root is on sys.path for all tests
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Force sample mode for all tests
os.environ.setdefault("SAMPLE_MODE", "true")
