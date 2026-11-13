import re, sys, httpx
from urllib.parse import urlparse

SKIP = ("bluesciencepark.se", "mtcos.se", "techconceptlab.com", "swedenict.se", "sisp.se",
        "facebook.com", "linkedin.com", "instagram.com", "youtube.com", "cookiedatabase.org",
        "google", "gstatic", "wp.com", "w.org", "jquery", "cloudflare")

def check(slug: str):
    url = f"https://www.bluesciencepark.se/medlem/{slug}/"
    html = httpx.get(url, timeout=20, follow_redirects=True,
                     headers={"User-Agent": "Mozilla/5.0 VSP-hackathon-bot/0.1"}).text
    links = sorted({h for h in re.findall(r'href=["\'](https?://[^"\'#]+)', html)
                    if not any(s in urlparse(h).netloc for s in SKIP)})
    has_industry = any(k in html.lower() for k in ("bransch", "anställda", "grundat"))
    print(f"\n=== {slug}  ({len(html)} bytes of HTML)")
    print(f" member fields present (bransch/anställda/grundat): {has_industry}")
    print(f" external links: {links if links else 'NONE FOUND'}")

for s in sys.argv[1:]:
    try:
        check(s)
    except Exception as e:
        print(f"\n=== {s}\n FAILED: {e}")
