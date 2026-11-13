import sys, re, httpx
from urllib.parse import urljoin, urlparse

url = sys.argv[1]
html = httpx.get(url, timeout=20, follow_redirects=True,
                 headers={"User-Agent": "VSP-hackathon-bot/0.1"}).text
links = sorted({urljoin(url, h) for h in re.findall(r'href=["\']([^"\'#]+)', html)})
keys = ("medlem", "member", "foretag", "företag", "companies", "company", "partner", "ekosystem", "hyresgast", "hyresgäst")
host = urlparse(url).netloc
for l in links:
    tag = "  <-- check" if any(k in l.lower() for k in keys) else ""
    if urlparse(l).netloc == host or tag:
        print(l + tag)
