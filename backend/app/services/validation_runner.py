"""
Automated quality validation: Lighthouse, axe-core, content checks.
Used by template validation pipeline (worker).
"""
from __future__ import annotations

import glob
import json
import logging
import os
import subprocess
import tempfile
import shutil
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Force Playwright to use Docker-installed browsers before any playwright import.
# Render can run with HOME=/opt/render; without this, Playwright looks under /opt/render/.cache.
if os.path.isdir("/app/.cache/ms-playwright"):
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "/app/.cache/ms-playwright"

logger = logging.getLogger(__name__)


def _find_chrome_path() -> Optional[str]:
    """Find Chrome/Chromium for Lighthouse. Uses CHROME_PATH env, or Playwright's bundled Chromium."""
    path = os.environ.get("CHROME_PATH")
    if path and os.path.isfile(path):
        return path
    # Fixed path used in Docker (PLAYWRIGHT_BROWSERS_PATH); then Render/home paths
    candidates = [
        "/app/.cache/ms-playwright/chromium-*/chrome-linux/chrome",
        os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "").rstrip("/") + "/chromium-*/chrome-linux/chrome",
        os.path.expanduser("~/.cache/ms-playwright/chromium-*/chrome-linux/chrome"),
        "/root/.cache/ms-playwright/chromium-*/chrome-linux/chrome",
        "/opt/render/.cache/ms-playwright/chromium-*/chrome-linux/chrome",
    ]
    for pattern in candidates:
        if not pattern or "*" not in pattern:
            continue
        matches = glob.glob(pattern)
        for m in matches:
            if os.path.isfile(m) and os.access(m, os.X_OK):
                return m
    # Fallback: scan known browser cache root for any chrome executable (e.g. nested under chromium-*)
    for root in ["/app/.cache/ms-playwright", os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "").rstrip("/")]:
        if not root or not os.path.isdir(root):
            continue
        for pattern in [os.path.join(root, "chromium-*", "chrome-linux", "chrome"), os.path.join(root, "*", "chrome-linux", "chrome")]:
            for m in glob.glob(pattern):
                if os.path.isfile(m) and os.access(m, os.X_OK):
                    return m
    # Fallback: chromium_headless_shell (Playwright 1.49+); Lighthouse may accept it on Linux
    for pattern in [
        "/app/.cache/ms-playwright/chromium_headless_shell-*/chrome-headless-shell-linux64/chrome-headless-shell",
        (os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "").rstrip("/") + "/chromium_headless_shell-*/chrome-headless-shell-linux64/chrome-headless-shell"),
    ]:
        if not pattern or "*" not in pattern:
            continue
        for m in glob.glob(pattern):
            if os.path.isfile(m) and os.access(m, os.X_OK):
                return m
    return None


def _find_lighthouse_cmd() -> Optional[str]:
    """Return path to lighthouse CLI, or None if not found."""
    cmd = shutil.which("lighthouse")
    if cmd:
        return cmd
    for path in ("/usr/local/bin/lighthouse", "/usr/bin/lighthouse"):
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    return None


def _normalize_thresholds(thresholds: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure lighthouse mins are 0-1 scale; timeouts present."""
    t = dict(thresholds or {})
    lh = t.get("lighthouse") or t.get("lighthouse_min") or {}
    if isinstance(lh, dict):
        out_lh = {}
        for k, v in lh.items():
            if isinstance(v, (int, float)) and v > 1:
                out_lh[k] = v / 100.0
            else:
                out_lh[k] = v
        t["lighthouse"] = out_lh
    axe = t.get("axe") or {}
    if not isinstance(axe, dict):
        axe = {}
    t["axe"] = {**{"critical_max": 0, "serious_max": 0, "moderate_max": 5}, **axe}
    content = t.get("content") or {}
    t["content"] = {
        "require_home": content.get("require_home", True),
        "require_cta": content.get("require_cta", True),
        "require_contact_or_lead": content.get("require_contact_or_lead", True),
        "require_mobile_meta": content.get("require_mobile_meta", True),
    }
    timeouts = t.get("timeouts") or {}
    t["timeouts"] = {"lighthouse_sec": 120, "axe_sec": 60, **timeouts}
    return t


def run_lighthouse(preview_url: str, timeouts: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
    """
    Run Lighthouse CLI on preview_url. Returns dict with scores (0-1) and key audits.
    On timeout or failure returns {"error": str, "scores": {}}.
    """
    result: Dict[str, Any] = {"scores": {}, "audits": {}}
    if not (preview_url.startswith("http://") or preview_url.startswith("https://")):
        result["error"] = "Lighthouse requires HTTP(S) URL"
        return result
    timeouts = timeouts or {}
    timeout_sec = timeouts.get("lighthouse_sec", 120)
    lighthouse_cmd = _find_lighthouse_cmd()
    if not lighthouse_cmd:
        result["error"] = "Lighthouse CLI not found. Install in Docker/build: npm install -g lighthouse"
        return result
    # Ensure Playwright browser path is set so _find_chrome_path() can locate Chromium
    if os.path.isdir("/app/.cache/ms-playwright"):
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "/app/.cache/ms-playwright"
    workdir = tempfile.mkdtemp(prefix="lighthouse_")
    report_path = os.path.join(workdir, "lighthouse-report.json")
    env = dict(os.environ)
    chrome_path = _find_chrome_path()
    if chrome_path:
        env["CHROME_PATH"] = chrome_path
    else:
        result["error"] = (
            "Chrome/Chromium not found for Lighthouse. Set CHROME_PATH in Render Environment to the path from: "
            "GET /api/debug/chrome-path (when logged in as Admin), or run in Render Shell: python scripts/print_chrome_path.py. "
            "If no path is found, ensure the backend uses Docker (not native Python) and the image installs Playwright chromium."
        )
        return result
    try:
        proc = subprocess.run(
            [
                lighthouse_cmd,
                preview_url,
                "--output=json",
                f"--output-path={report_path}",
                "--quiet",
                "--chrome-flags=--headless --no-sandbox --disable-dev-shm-usage",
            ],
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            cwd=workdir,
            env=env,
        )
        if proc.returncode != 0:
            stderr = (proc.stderr or "").strip() or (proc.stdout or "").strip()
            hint = ""
            if "CHROME_PATH" in stderr:
                hint = " (Set CHROME_PATH to a Chrome/Chromium executable, or ensure Playwright chromium is installed: python -m playwright install chromium)"
            elif "ECONNREFUSED" in stderr or "connection" in stderr.lower() or "Unable to connect" in stderr:
                hint = " (Preview URL must be reachable from this process; in Docker set BACKEND_URL to the backend service URL, e.g. http://backend:8000)"
            result["error"] = f"Lighthouse failed: exit {proc.returncode}. {stderr[:500]}{hint}"
            return result
    except subprocess.TimeoutExpired:
        result["error"] = f"Lighthouse timed out after {timeout_sec}s"
        return result
    except FileNotFoundError as e:
        result["error"] = f"Lighthouse executable not found: {e}. Install in build: npm install -g lighthouse"
        return result
    except Exception as e:
        result["error"] = str(e)
        return result
    try:
        with open(report_path, "r", encoding="utf-8") as f:
            report = json.load(f)
    except Exception as e:
        result["error"] = f"Failed to read report: {e}"
        return result
    finally:
        try:
            if os.path.exists(report_path):
                os.remove(report_path)
            os.rmdir(workdir)
        except OSError:
            pass
    categories = report.get("categories", {})
    for name, key in [
        ("performance", "performance"),
        ("accessibility", "accessibility"),
        ("seo", "seo"),
        ("best_practices", "best-practices"),
    ]:
        cat = categories.get(key, {})
        score = cat.get("score")
        if score is not None:
            result["scores"][name] = score
    result["audits"] = {k: v for k, v in list(report.get("audits", {}).items())[:20]}
    return result


def run_axe(preview_url: str, timeouts: Optional[Dict[str, int]] = None) -> Dict[str, Any]:
    """
    Run axe-core via Playwright. Returns counts (critical, serious, moderate, minor) and top violations.
    """
    result: Dict[str, Any] = {"critical": 0, "serious": 0, "moderate": 0, "minor": 0, "violations": []}
    if not (preview_url.startswith("http://") or preview_url.startswith("https://")):
        result["error"] = "Axe requires HTTP(S) URL"
        return result
    timeout_sec = (timeouts or {}).get("axe_sec", 60)
    # Ensure Playwright uses our browser dir (again right before use, in case env was lost in worker)
    if os.path.isdir("/app/.cache/ms-playwright"):
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "/app/.cache/ms-playwright"
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        result["error"] = "Playwright not installed"
        return result
    chrome_path = _find_chrome_path()
    launch_options: Dict[str, Any] = {"headless": True}
    if chrome_path:
        launch_options["executable_path"] = chrome_path
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(**launch_options)
            try:
                page = browser.new_page()
                page.goto(preview_url, wait_until="domcontentloaded", timeout=min(timeout_sec * 1000, 30000))
                page.add_script_tag(url="https://cdnjs.cloudflare.com/ajax/libs/axe-core/4.8.2/axe.min.js")
                axe_result = page.evaluate("async () => await axe.run()")
            finally:
                browser.close()
    except Exception as e:
        result["error"] = str(e)
        return result
    violations = axe_result.get("violations") or []
    for v in violations:
        impact = (v.get("impact") or "minor").lower()
        if impact in result:
            result[impact] = result[impact] + 1
        else:
            result["minor"] = result.get("minor", 0) + 1
    result["violations"] = [
        {"id": v.get("id"), "impact": v.get("impact"), "description": v.get("description"), "help": v.get("help")}
        for v in violations[:15]
    ]
    return result


def run_content_checks(preview_url: str) -> Dict[str, Any]:
    """
    Fetch HTML and parse: home exists, CTA, contact/lead form, viewport meta, nav links.
    """
    result: Dict[str, Any] = {
        "has_home": False,
        "has_cta": False,
        "has_contact_or_lead": False,
        "has_viewport_meta": False,
        "nav_links_ok": True,
        "details": [],
    }
    if not (preview_url.startswith("http://") or preview_url.startswith("https://")):
        result["error"] = "Content checks require HTTP(S) URL"
        return result
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        result["error"] = "requests/beautifulsoup4 required"
        return result
    try:
        resp = requests.get(preview_url, timeout=15)
        resp.raise_for_status()
        html = resp.text
    except Exception as e:
        result["error"] = str(e)
        return result
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        soup = BeautifulSoup(html, "html.parser")
    body = soup.find("body") or soup
    text_lower = body.get_text().lower() if body else ""
    links = soup.find_all("a", href=True)
    forms = soup.find_all("form")
    buttons = soup.find_all("button") + [a for a in links if (a.get_text() or "").strip().lower() in ("get started", "contact", "sign up", "learn more", "cta")]
    meta_viewport = soup.find("meta", attrs={"name": "viewport"})
    result["has_viewport_meta"] = meta_viewport is not None
    if not result["has_viewport_meta"]:
        result["details"].append("viewport meta tag missing")
    result["has_home"] = "home" in text_lower or any(
        (href or "").lower().endswith("home") or "home" in (href or "").lower() for _, href in [(a.get_text(), a.get("href")) for a in links]
    )
    if not result["has_home"]:
        result["details"].append("home link or content not found")
    cta_keywords = ["get started", "contact us", "sign up", "learn more", "cta", "book now", "request"]
    result["has_cta"] = any(kw in text_lower for kw in cta_keywords) or len(buttons) > 0
    if not result["has_cta"]:
        result["details"].append("no CTA button/link found")
    result["has_contact_or_lead"] = len(forms) > 0 or "contact" in text_lower or "mailto:" in html
    if not result["has_contact_or_lead"]:
        result["details"].append("no contact form or lead form found")
    return result


def aggregate_results(
    lh: Dict[str, Any],
    axe: Dict[str, Any],
    content: Dict[str, Any],
    thresholds: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Build validation summary. thresholds: normalized (lighthouse, axe, content, timeouts).
    Returns: lighthouse, axe, content, thresholds, passed, failed_reasons, run_at.
    """
    thresholds = _normalize_thresholds(thresholds)
    run_at = datetime.now(timezone.utc).isoformat()
    failed_reasons: List[str] = []
    lh_req = thresholds.get("lighthouse") or thresholds.get("lighthouse_min") or {}
    axe_req = thresholds.get("axe") or {}
    content_req = thresholds.get("content") or {}

    if lh.get("error"):
        failed_reasons.append(f"Lighthouse: {lh['error']}")
    else:
        scores = lh.get("scores") or {}
        for score_name, min_val in [
            ("performance", lh_req.get("performance_min") or lh_req.get("performance")),
            ("accessibility", lh_req.get("accessibility_min") or lh_req.get("accessibility")),
            ("seo", lh_req.get("seo_min") or lh_req.get("seo")),
            ("best_practices", lh_req.get("best_practices_min") or lh_req.get("best_practices")),
        ]:
            if min_val is None:
                continue
            s = scores.get(score_name)
            if s is not None:
                m = min_val if min_val <= 1 else min_val / 100
                if s < m:
                    failed_reasons.append(f"Lighthouse {score_name} {s:.2f} below {m}")

    if axe.get("error"):
        failed_reasons.append(f"Axe: {axe['error']}")
    else:
        if axe.get("critical", 0) > axe_req.get("critical_max", 0):
            failed_reasons.append(f"Axe critical violations: {axe.get('critical')} (max {axe_req.get('critical_max')})")
        if axe.get("serious", 0) > axe_req.get("serious_max", 0):
            failed_reasons.append(f"Axe serious violations: {axe.get('serious')} (max {axe_req.get('serious_max')})")
        if axe.get("moderate", 0) > axe_req.get("moderate_max", 5):
            failed_reasons.append(f"Axe moderate violations: {axe.get('moderate')} (max {axe_req.get('moderate_max')})")

    if content.get("error"):
        failed_reasons.append(f"Content: {content['error']}")
    else:
        if content_req.get("require_home") and not content.get("has_home"):
            failed_reasons.append("Content: home not found")
        if content_req.get("require_cta") and not content.get("has_cta"):
            failed_reasons.append("Content: CTA not found")
        if content_req.get("require_contact_or_lead") and not content.get("has_contact_or_lead"):
            failed_reasons.append("Content: contact/lead form not found")
        if content_req.get("require_mobile_meta") and not content.get("has_viewport_meta"):
            failed_reasons.append("Content: viewport meta missing")

    passed = len(failed_reasons) == 0
    return {
        "lighthouse": lh,
        "axe": axe,
        "content": content,
        "thresholds": thresholds,
        "passed": passed,
        "failed_reasons": failed_reasons,
        "run_at": run_at,
    }
