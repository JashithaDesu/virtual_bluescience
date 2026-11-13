"""Fetch company website pages into the cache. Rejects cookie banners and duplicates."""
import json, hashlib, datetime, pathlib, re
import httpx, trafilatura

HERE = pathlib.Path(__file__).parent
CACHE = HERE / "cache"
CACHE.mkdir(exist_ok=True)
CONSENT = ("cookies", "samtycke", "consent", "enhetsinformation", "surfbeteende")
MIN_CHARS = 300

def looks_like_consent(text: str) -> bool:
    head = text[:600].lower()
    return sum(w in head for w in CONSENT) >= 2

def fetch_page(company_id: str, url: str, seen: set) -> dict | None:
    r = httpx.get(url, timeout=20, follow_redirects=True,
                  headers={"User-Agent": "Mozilla/5.0 VSP-hackathon-bot/0.1"})
    r.raise_for_status()
    text = trafilatura.extract(r.text, include_comments=False, include_tables=True) or ""
    text = re.sub(r"[ \t]+", " ", text).strip()
    h = hashlib.sha256(text.encode()).hexdigest()
    if len(text) < MIN_CHARS:
        print(f"  REJECT too short ({len(text)} chars): {url}"); return None
    if looks_like_consent(text):
        print(f"  REJECT cookie/consent text: {url}"); return None
    if h in seen:
        print(f"  REJECT duplicate content: {url}"); return None
    seen.add(h)
    rec = {
        "company_id": company_id,
        "source_url": str(r.url),
        "source_type": "company_website",
        "retrieved_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "content_hash": h,
        "chars": len(text),
        "text": text,
    }
    name = f"site_{company_id}_{hashlib.md5(url.encode()).hexdigest()[:8]}.json"
    (CACHE / name).write_text(json.dumps(rec, ensure_ascii=False, indent=2))
    return rec

if __name__ == "__main__":
    companies = json.loads((HERE / "companies.json").read_text())
    seen: set = set()
    for cid, c in companies.items():
        print(f"\n=== {cid}")
        for url in c["pages"]:
            try:
                rec = fetch_page(cid, url, seen)
                if rec:
                    print(f"  OK {rec['chars']} chars  hash={rec['content_hash'][:10]}  {url}")
            except Exception as e:
                print(f"  FAILED {url}: {e}")
