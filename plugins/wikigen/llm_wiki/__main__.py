"""Allow ``python -m llm_wiki`` to invoke the CLI."""

from __future__ import annotations

import sys

from llm_wiki.cli import main

if __name__ == "__main__":
    sys.exit(main())
