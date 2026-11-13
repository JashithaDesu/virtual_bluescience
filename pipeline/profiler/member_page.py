"""Parse a Blue Science Park member page: description text, website, field hints."""
import sys, re, json, hashlib, datetime, pathlib
from urllib.parse import urlparse
import httpx
from bs4 import BeautifulSoup

SKIP = ("bluesciencepark.se", "mtcos.se", "techconceptlab.com", "swedenict.se", "sisp.se",
        "facebook.com", "linkedin.com", "instagram.com", "youtube.com")
PREFIXES = {"antal-anstallda-": "employees", "bransch-": "industry", "ort-": "location"}
CACHE = pathlib.Path(__file__).parent / "cache"
CACHE.mkdir(exist_ok=True)

def parse_member(slug: str) -> dict:
    url = f"https://www.bluesciencepark.se/medlem/{slug}/"
    html = httpx.get(url, timeout=20, follow_redirects=True,
                     headers={"User-Agent": "Mozilla/5.0 VSP-hackathon-bot/0.1"}).text
    soup = BeautifulSoup(html, "html.parser")
    block = soup.find("div", attrs={"data-elementor-type": "single-post"})
    if block is None:
        raise ValueError("member block not found")

    hints = {}
    for cls in block.get("class", []):
        for p, name in PREFIXES.items():
            if cls.startswith(p):
                hints.setdefault(name, []).append(cls[len(p):])

    website = next((a["href"] for a in block.find_all("a", href=True)
                    if a["href"].startswith("http") and not any(s in urlparse(a["href"]).netloc for s in SKIP)), None)

    for t in block(["script", "style", "noscript", "svg"]):
        t.decompose()
    text = re.sub(r"\s+", " ", block.get_text(" ", strip=True))
    text = text.split("Fler medlemmar")[0]                  # drop the "more members" list
    text = re.sub(r"^\s*Till medlemmar\s*", "", text).strip()  # drop the back-link label

    rec = {
        "company_id": slug,
        "source_url": url,
        "source_type": "bsp_member_page",
        "retrieved_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "content_hash": hashlib.sha256(text.encode()).hexdigest(),
        "hints": hints,
        "website": website,
        "chars": len(text),
        "text": text,
    }
    (CACHE / f"member_{slug}.json").write_text(json.dumps(rec, ensure_ascii=False, indent=2))
    return rec

if __name__ == "__main__":
    for slug in sys.argv[1:]:
        try:
            r = parse_member(slug)
            print(f"\n=== {slug}  chars={r['chars']}  hash={r['content_hash'][:10]}")
            print(" hints  :", r["hints"])
            print(" website:", r["website"])
            print(" text   :", r["text"])
        except Exception as e:
            print(f"\n=== {slug}\n FAILED: {e}")
