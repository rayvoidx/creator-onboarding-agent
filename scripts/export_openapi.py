"""
Export FastAPI OpenAPI schema to a JSON file without running the server.

Usage:
  python scripts/export_openapi.py node/src/types/openapi.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


def main() -> int:
    try:
        # Import the FastAPI app
        from main import app  # type: ignore
    except Exception as e:
        print(f"Failed to import FastAPI app from main.py: {e}", file=sys.stderr)
        return 1

    try:
        openapi = app.openapi()
    except Exception as e:
        print(f"Failed to generate OpenAPI schema: {e}", file=sys.stderr)
        return 1

    out_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("node/src/types/openapi.json")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(openapi, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"OpenAPI schema written to {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


