"""Public-source fetcher. No LLM or database calls."""
import argparse
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urldefrag, urljoin, urlsplit

import httpx
from bs4 import BeautifulSoup

CACHE = Path(__file__).resolve().parent / ".cache"
EVENTS = "https://www.bluesciencepark.se/event/"
FUNDING = "https://www.energimyndigheten.se/utlysningar/"
OFFERS = [
    "https://www.bluesciencepark.se/vara-tjanster/test-utveckling/",
    "https://www.bluesciencepark.se/projekt-erbjudande/",
]
REMOVE = (
    "script, style, nav, footer, "
    "[class*='cmplz'], [id*='cmplz'], "
    "#onetrust-banner-sdk, #CybotCookiebotDialog"
)


def fetch(client, url, refresh=False):
    url = urldefrag(url)[0]
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / (hashlib.sha256(url.encode()).hexdigest() + ".json")
    if path.exists() and not refresh:
        cached = json.loads(path.read_text(encoding="utf-8"))
        age = datetime.now(timezone.utc) - datetime.fromisoformat(
            cached["retrieved_at"]
        )
        if age < timedelta(hours=6):
            print("CACHE", url)
            return cached

    response = client.get(url)
    response.raise_for_status()
    retrieved_at = datetime.now(timezone.utc).isoformat()
    soup = BeautifulSoup(response.text, "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    host = urlsplit(str(response.url)).hostname or ""

    selectors = (
        ['[data-elementor-type="wp-page"]',
         '[data-elementor-type="single-page"]', "main", "#content"]
        if host.endswith("bluesciencepark.se")
        else ["#proclamation-archive-page", "main", "[role='main']", "#content"]
    )
    root = next(
        (node for selector in selectors
         if (node := soup.select_one(selector)) is not None),
        None,
    )
    if root is None:
        raise ValueError(f"No verified content container: {url}")

    for node in root.select(REMOVE):
        node.decompose()

    text = root.get_text("\n", strip=True)
    if len(text) < 100:
        raise ValueError(f"Too little content: {url}")

    links = []
    seen = set()
    for anchor in root.select("a[href]"):
        target = urldefrag(urljoin(str(response.url), anchor["href"]))[0]
        label = anchor.get_text(" ", strip=True)
        if not label or target in seen:
            continue
        if urlsplit(target).scheme not in {"http", "https"}:
            continue
        seen.add(target)
        links.append({"title": label, "url": target})

    result = {
        "requested_url": url,
        "url": str(response.url),
        "title": title,
        "retrieved_at": retrieved_at,
        "content_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "text": text,
        "links": links,
    }
    path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("FETCH", response.status_code, url, f"({len(text)} chars)")
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true")
    args = parser.parse_args()
    pages = []
    failures = []

    with httpx.Client(
        follow_redirects=True,
        timeout=45,
        headers={"User-Agent": "VirtualSciencePark-Hackathon/0.1"},
    ) as client:
        def collect(url):
            try:
                page = fetch(client, url, args.refresh)
                pages.append(page)
                return page
            except (httpx.HTTPError, ValueError) as exc:
                failures.append({"url": url, "error": str(exc)})
                print("FAILED", url, str(exc))
                return None

        events = collect(EVENTS)
        funding = collect(FUNDING)

        if funding:
            candidates = [
                link for link in funding["links"]
                if urlsplit(link["url"]).hostname == "www.energimyndigheten.se"
                and urlsplit(link["url"]).path.startswith("/utlysningar/")
                and urlsplit(link["url"]).path.rstrip("/") != "/utlysningar"
                and "stänger" in link["title"].lower()
            ]
            print("Funding candidates with closing-date labels:", len(candidates))
            for link in candidates[:9]:
                collect(link["url"])

        for url in OFFERS:
            collect(url)

        if events:
            for link in events["links"]:
                if "onsdagslunch" in urlsplit(link["url"]).path:
                    collect(link["url"])

    manifest = {"pages": pages, "failures": failures}
    target = CACHE / "manifest.json"
    target.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\nSaved {len(pages)} pages; {len(failures)} failures.")
    print("Manifest:", target)
    for page in pages:
        print("-", page["title"], "|", page["retrieved_at"])
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
