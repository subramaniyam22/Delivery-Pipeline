#!/usr/bin/env python3
"""
End-to-end pipeline simulation: create a project, optionally complete onboarding,
run autopilot sweeper and job processing until project reaches COMPLETE, HOLD, or NEEDS_REVIEW.
Requires: backend running (API), DB and Redis. Use for local or Render verification.

Usage:
  # With backend at localhost:8000 (create project only; print status)
  python scripts/e2e_pipeline_simulation.py --base-url http://localhost:8000 --create-only

  # Create project + run sweeper N times (no worker; sweeper only enqueues)
  python scripts/e2e_pipeline_simulation.py --base-url http://localhost:8000 --sweeps 5

  # Requires valid JWT (login first or set AUTH_HEADER)
  export AUTH_HEADER="Bearer <jwt>"
  python scripts/e2e_pipeline_simulation.py --base-url http://localhost:8000
"""
from __future__ import annotations

import argparse
import os
import sys
import time

try:
    import requests
except ImportError:
    print("Install requests: pip install requests")
    sys.exit(1)

def main():
    p = argparse.ArgumentParser(description="E2E pipeline simulation")
    p.add_argument("--base-url", default=os.environ.get("BACKEND_URL", "http://localhost:8000"), help="Backend base URL")
    p.add_argument("--auth", default=os.environ.get("AUTH_HEADER"), help="Authorization header (Bearer <token>)")
    p.add_argument("--create-only", action="store_true", help="Only create project and print status")
    p.add_argument("--sweeps", type=int, default=0, help="Run autopilot sweeper this many times (interval 5s)")
    args = p.parse_args()

    base = args.base_url.rstrip("/")
    headers = {}
    if args.auth:
        headers["Authorization"] = args.auth

    # 1) Create project (Sales handover -> ONBOARDING)
    print("Creating project (Sales handover)...")
    r = requests.post(
        f"{base}/projects",
        json={
            "title": "E2E Simulation Project",
            "description": "Created by e2e_pipeline_simulation",
            "client_name": "E2E Client",
            "priority": "MEDIUM",
            "status": "ACTIVE",
            "project_type": "Full Website",
            "pmc_name": "PMC",
            "location": "US",
            "client_email_ids": "client@example.com",
        },
        headers=headers,
        timeout=30,
    )
    if r.status_code not in (200, 201):
        print(f"Create project failed: {r.status_code} {r.text}")
        return 1
    project = r.json()
    project_id = project["id"]
    print(f"Project id={project_id} status={project.get('status')} current_stage={project.get('current_stage')}")

    if args.create_only:
        print("Done (create-only). Check UI or run worker + sweeper to advance.")
        return 0

    # 2) Optional: run sweeper (backstop) N times
    for i in range(args.sweeps):
        try:
            r = requests.post(
                f"{base}/projects/{project_id}/pipeline/advance",
                json={},
                headers=headers,
                timeout=15,
            )
            if r.status_code == 200:
                st = r.json()
                print(f"  Sweep {i+1}: next_ready={st.get('next_ready_stages')} blocked={st.get('blocked_summary')}")
        except Exception as e:
            print(f"  Sweep {i+1} error: {e}")
        time.sleep(5)

    # 3) Final project status
    r = requests.get(f"{base}/projects/{project_id}", headers=headers, timeout=10)
    if r.status_code == 200:
        p = r.json()
        print(f"Final: status={p.get('status')} stage={p.get('current_stage')} hold_reason={p.get('hold_reason')} needs_review_reason={p.get('needs_review_reason')} defect_cycle_count={p.get('defect_cycle_count')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
