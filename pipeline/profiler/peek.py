import sys, re, httpx
html = httpx.get(f"https://www.bluesciencepark.se/medlem/{sys.argv[1]}/", timeout=20,
                 follow_redirects=True, headers={"User-Agent": "Mozilla/5.0 VSP-hackathon-bot/0.1"}).text
i = html.lower().find("bransch")
chunk = html[max(0, i - 1500): i + 1500]
chunk = re.sub(r"\s+", " ", chunk)
print(chunk)
