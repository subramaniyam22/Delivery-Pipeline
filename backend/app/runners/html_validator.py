from typing import Any, Dict, List
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


def validate_html(preview_url: str) -> List[Dict[str, Any]]:
    checks: List[Dict[str, Any]] = []
    if preview_url.startswith("file://"):
        path = preview_url.replace("file://", "")
        with open(path, "r", encoding="utf-8") as handle:
            html = handle.read()
    else:
        resp = requests.get(preview_url, timeout=20)
        resp.raise_for_status()
        html = resp.text
    soup = BeautifulSoup(html, "lxml")

    title = soup.find("title")
    checks.append({
        "name": "title_tag",
        "passed": bool(title and title.text.strip()),
        "details": "Title tag present" if title else "Missing title tag",
    })

    description = soup.find("meta", attrs={"name": "description"})
    checks.append({
        "name": "meta_description",
        "passed": bool(description and description.get("content")),
        "details": "Meta description present" if description else "Missing meta description",
    })

    canonical = soup.find("link", rel="canonical")
    checks.append({
        "name": "canonical_link",
        "passed": bool(canonical and canonical.get("href")),
        "details": "Canonical link present" if canonical else "Missing canonical link",
    })

    images = soup.find_all("img")
    missing_alt = [img.get("src") for img in images if not img.get("alt")]
    checks.append({
        "name": "image_alt_tags",
        "passed": len(missing_alt) == 0,
        "details": f"Missing alt on {len(missing_alt)} images" if missing_alt else "All images have alt",
    })

    broken_links: List[str] = []
    for link in soup.find_all("a"):
        href = link.get("href")
        if not href or href.startswith("#") or href.startswith("mailto:"):
            continue
        if href.startswith("/"):
            url = urljoin(preview_url, href)
            try:
                link_resp = requests.head(url, timeout=10)
                if link_resp.status_code >= 400:
                    broken_links.append(href)
            except Exception:
                broken_links.append(href)
    checks.append({
        "name": "broken_internal_links",
        "passed": len(broken_links) == 0,
        "details": f"Broken links: {broken_links}" if broken_links else "No broken internal links",
    })

    return checks
