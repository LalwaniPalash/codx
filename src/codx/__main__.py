#!/usr/bin/env python3
"""Entry point for codx when run as a module or standalone executable."""

import sys
from pathlib import Path

# Add the src directory to the path for proper imports
src_dir = Path(__file__).parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from codx.cli.commands import app

if __name__ == "__main__":
    app()