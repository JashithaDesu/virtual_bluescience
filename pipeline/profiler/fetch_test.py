import sys, json, hashlib, datetime, pathlib
import httpx, trafilatura

CACHE = pathlib.Path("cache")
CACHE.mkdir(exist_ok=True)

def fetch(url: str) -> dict:
    r = httpx.get(url, timeout=20, follow_redirects=True,
                  headers={"User-Agent": "VSP-hackathon-bot/0.1"})
    r.raise_for_status()
    text = trafilatura.extract(r.text, include_comments=False, include_tables=True) or ""
    rec = {
        "url": url,
        "retrieved_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "content_hash": hashlib.sha256(text.encode()).hexdigest(),
        "chars": len(text),
        "text": text,
    }
    name = hashlib.md5(url.encode()).hexdigest()[:12] + ".json"
    (CACHE / name).write_text(json.dumps(rec, ensure_ascii=False, indent=2))
    return rec

if __name__ == "__main__":
    for url in sys.argv[1:]:
        try:
            rec = fetch(url)
            print(f"\n=== {url}\n chars={rec['chars']}  hash={rec['content_hash'][:10]}")
            print(" " + rec["text"][:300].replace("\n", " ") + " ...")
        except Exception as e:
            print(f"\n=== {url}\n FAILED: {e}")
