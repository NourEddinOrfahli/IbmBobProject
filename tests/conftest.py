"""
pytest configuration for Space Interpreter tests.

Adds the backend/ directory to sys.path so that all test modules can
import backend modules directly without relative-path hacks in each file.
"""

import sys
import os

# Insert backend/ at the front of the path so imports resolve correctly
# regardless of which directory pytest is invoked from.
_backend_dir = os.path.join(os.path.dirname(__file__), "..", "backend")
_backend_dir = os.path.abspath(_backend_dir)

if _backend_dir not in sys.path:
    sys.path.insert(0, _backend_dir)
