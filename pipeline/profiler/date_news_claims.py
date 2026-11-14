"""Add the article publication date to claims sourced from BSP news. Updates value/confidence only; ids unchanged."""
import re, sys, pathlib, datetime
import httpx
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from pipeline.common import db

UA = {"User-Agent": "Mozilla/5.0 VSP-hackathon-bot/0.1"}
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

def published(url):
    html = httpx.get(url, timeout=20, follow_redirects=True, headers=UA).text
    m = re.search(r'article:published_time"\s+content="(\d{4})-(\d{2})-(\d{2})', html) or \
        re.search(r'"datePublished"\s*:\s*"(\d{4})-(\d{2})-(\d{2})', html)
    return (int(m.group(1)), int(m.group(2))) if m else None

def main(cid, apply):
    rows = db.client().table("profile_claims").select("id,field,value,type,confidence,source_url") \
        .eq("company_id", cid).like("source_url", "%/aktuellt/%").execute().data
    dates = {}
    for r in rows:
        url = r["source_url"]
        if url not in dates:
            dates[url] = published(url)
        d = dates[url]
        if not d or r["field"] == "domain" or "(BSP news" in (r["value"] or ""):
            print(f"  skip  {r['field']:<14} {r['value']}  (date={d})")
            continue
        new_value = f"{r['value']} (BSP news, {MONTHS[d[1]-1]} {d[0]})"
        age = datetime.date.today().year - d[0]
        new_conf = "low" if r["field"] == "priority" and age >= 2 else r["confidence"]
        print(f"  {'SET ' if apply else 'PLAN'}  {r['field']:<14} {new_value}  confidence={new_conf}")
        if apply:
            db.client().table("profile_claims").update({"value": new_value, "confidence": new_conf}).eq("id", r["id"]).execute()

if __name__ == "__main__":
    main(sys.argv[1], "--apply" in sys.argv)
