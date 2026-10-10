#!/usr/bin/env python3
"""Compatibility shim: `python server.py` still works for configs created before 1.0.

The server lives in src/rmp_mcp/. Prefer the `rmp-mcp` console script or `uvx rmp-mcp`.
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

from rmp_mcp.server import main  # noqa: E402

if __name__ == "__main__":
    main()
