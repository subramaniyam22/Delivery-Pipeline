import os
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright


def _load_image(path: str) -> np.ndarray:
    image = Image.open(path).convert("RGB")
    return np.array(image)


def _diff_score(img_a: np.ndarray, img_b: np.ndarray) -> float:
    resized_b = cv2.resize(img_b, (img_a.shape[1], img_a.shape[0]))
    diff = cv2.absdiff(img_a, resized_b)
    return float(np.mean(diff) / 255.0)


def capture_screenshot(preview_url: str, output_path: str) -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(preview_url, wait_until="networkidle")
        page.set_viewport_size({"width": 1280, "height": 720})
        page.screenshot(path=output_path, full_page=True)
        browser.close()


def run_visual_regression(
    preview_url: str,
    baseline_dir: Optional[str],
    workdir: str,
) -> Tuple[List[Dict[str, Any]], Optional[str], Optional[str]]:
    checks: List[Dict[str, Any]] = []
    screenshot_path = os.path.join(workdir, "current.png")
    capture_screenshot(preview_url, screenshot_path)

    if not baseline_dir or not os.path.exists(baseline_dir):
        checks.append({
            "name": "visual_regression_baseline",
            "passed": True,
            "details": "No baseline available, visual regression is informational",
            "informational": True,
        })
        return checks, screenshot_path, None

    baseline_path = os.path.join(baseline_dir, "baseline.png")
    if not os.path.exists(baseline_path):
        checks.append({
            "name": "visual_regression_baseline",
            "passed": True,
            "details": "Baseline file not found, visual regression is informational",
            "informational": True,
        })
        return checks, screenshot_path, None

    img_a = _load_image(baseline_path)
    img_b = _load_image(screenshot_path)
    score = _diff_score(img_a, img_b)
    checks.append({
        "name": "visual_regression_diff",
        "passed": score <= 0.05,
        "details": f"Diff score {score:.3f}",
        "score": score,
    })
    diff_path = os.path.join(workdir, "diff.png")
    diff_img = cv2.absdiff(img_a, cv2.resize(img_b, (img_a.shape[1], img_a.shape[0])))
    cv2.imwrite(diff_path, diff_img)
    return checks, screenshot_path, diff_path
