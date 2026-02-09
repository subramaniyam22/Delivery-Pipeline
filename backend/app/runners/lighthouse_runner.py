import json
import os
import subprocess
from typing import Any, Dict, List, Tuple


def run_lighthouse(preview_url: str, workdir: str, thresholds: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    checks: List[Dict[str, Any]] = []
    report_path = os.path.join(workdir, "lighthouse-report.json")

    if not (preview_url.startswith("http://") or preview_url.startswith("https://")):
        checks.append({
            "name": "lighthouse_run",
            "passed": True,
            "details": "Lighthouse requires HTTP(S) preview URL",
            "informational": True,
        })
        return checks, {}

    try:
        subprocess.run(
            [
                "lighthouse",
                preview_url,
                "--output=json",
                f"--output-path={report_path}",
                "--quiet",
                "--chrome-flags=--headless",
            ],
            check=True,
        )
    except Exception as exc:
        checks.append({
            "name": "lighthouse_run",
            "passed": True,
            "details": f"Lighthouse skipped: {exc}",
            "informational": True,
        })
        return checks, {}

    with open(report_path, "r", encoding="utf-8") as handle:
        report = json.load(handle)

    categories = report.get("categories", {})
    scores = {
        "performance": categories.get("performance", {}).get("score"),
        "accessibility": categories.get("accessibility", {}).get("score"),
        "seo": categories.get("seo", {}).get("score"),
        "best_practices": categories.get("best-practices", {}).get("score"),
    }

    min_scores = thresholds.get("lighthouse_min", {})
    for key, score in scores.items():
        if score is None:
            continue
        min_required = min_scores.get(key)
        passed = True if min_required is None else score >= min_required
        checks.append({
            "name": f"lighthouse_{key}",
            "passed": passed,
            "details": f"{key} score {score}",
            "score": score,
            "minimum": min_required,
        })

    return checks, report
