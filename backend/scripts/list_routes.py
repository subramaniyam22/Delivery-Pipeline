#!/usr/bin/env python
"""
List all API routes (path, methods) for the FastAPI app.
Use this to keep docs/routes-permissions.md in sync when adding new endpoints.
Run from repo root: python -m backend.scripts.list_routes
Or from backend: python scripts/list_routes.py (with PYTHONPATH=.)
"""
import sys
from pathlib import Path

# Ensure backend/app is importable
backend = Path(__file__).resolve().parent.parent
if str(backend) not in sys.path:
    sys.path.insert(0, str(backend.parent))

from fastapi import FastAPI
from app.main import app


def list_routes(app: FastAPI) -> list[tuple[str, str, str]]:
    out = []
    for route in app.routes:
        if hasattr(route, "path") and hasattr(route, "methods"):
            path = route.path.replace("//", "/")
            methods = ",".join(sorted(m for m in route.methods if m != "HEAD"))
            name = getattr(route, "name", "") or ""
            out.append((path, methods, name))
    return sorted(out, key=lambda x: (x[0], x[1]))


def main():
    rows = list_routes(app)  # app has routes with full path from include_router
    print("# API routes (path, methods, name)")
    print()
    for path, methods, name in rows:
        print(f"{path}\t{methods}\t{name}")


if __name__ == "__main__":
    main()
