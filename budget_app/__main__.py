"""`python -m budget_app` 진입점."""

from __future__ import annotations

import sys

from budget_app.cli import main

if __name__ == "__main__":
    sys.exit(main())
