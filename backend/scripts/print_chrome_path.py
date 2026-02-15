#!/usr/bin/env python3
"""
Print the Chrome/Chromium path used for Lighthouse (e.g. for CHROME_PATH on Render).
Run from backend dir: python scripts/print_chrome_path.py
Or in Render Shell: python scripts/print_chrome_path.py
"""
import os
import glob


def find_chrome_path():
    path = os.environ.get("CHROME_PATH")
    if path and os.path.isfile(path):
        return path
    if os.path.isdir("/app/.cache/ms-playwright"):
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "/app/.cache/ms-playwright"
    root = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "").rstrip("/") or "/app/.cache/ms-playwright"
    for pattern in [
        f"{root}/chromium-*/chrome-linux/chrome",
        "/app/.cache/ms-playwright/chromium-*/chrome-linux/chrome",
        os.path.expanduser("~/.cache/ms-playwright/chromium-*/chrome-linux/chrome"),
    ]:
        if not pattern or "*" not in pattern:
            continue
        for m in glob.glob(pattern):
            if os.path.isfile(m) and os.access(m, os.X_OK):
                return m
    for r in [root, "/app/.cache/ms-playwright"]:
        if not r or not os.path.isdir(r):
            continue
        for p in [
            os.path.join(r, "chromium-*", "chrome-linux", "chrome"),
            os.path.join(r, "*", "chrome-linux", "chrome"),
            os.path.join(r, "chromium_headless_shell-*", "chrome-headless-shell-linux64", "chrome-headless-shell"),
        ]:
            for m in glob.glob(p):
                if os.path.isfile(m) and os.access(m, os.X_OK):
                    return m
    return None


if __name__ == "__main__":
    chrome = find_chrome_path()
    pw = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "")
    print("PLAYWRIGHT_BROWSERS_PATH:", pw or "(not set)")
    print("CHROME_PATH (use this in Render Environment):", chrome or "(not found)")
    if chrome:
        print("\nAdd in Render → Backend → Environment:")
        print("  Key:   CHROME_PATH")
        print("  Value:", chrome)
