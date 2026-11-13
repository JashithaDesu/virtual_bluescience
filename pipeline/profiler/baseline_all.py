"""Baseline profiles for ALL BSP members from their BSP member pages only.
FILES ONLY: writes out/baseline/. Never touches the database. Demo companies are skipped."""
import re, sys, json, time, shutil, pathlib, collections
from concurrent.futures import ThreadPoolExecutor
import httpx

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from pipeline.profiler.member_page import parse_member
from pipeline.profiler import profiler as P
P.SKIP_TOPICS = True

BASE = P.OUT / "baseline"
BASE.mkdir(parents=True, exist_ok=True)
DEMO = {"ocean-harvesting", "addsecure", "malvacom"}
UA = {"User-Agent": "Mozilla/5.0 VSP-hackathon-bot/0.1"}

def member_slugs():
    slugs = set()
    for url in ("https://www.bluesciencepark.se/", "https://www.bluesciencepark.se/bli-medlem/"):
        html = httpx.get(url, timeout=20, follow_redirects=True, headers=UA).text
        slugs |= set(re.findall(r"bluesciencepark\.se/medlem/([a-z0-9\-]+)/", html))
    return sorted(slugs)

def one(slug):
    if slug in DEMO:
        return slug, "skip (demo company)"
    try:
        parse_member(slug)
        P.profile(slug, slug.replace("-", " ").title())
        shutil.move(str(P.OUT / f"profile_{slug}.json"), BASE / f"profile_{slug}.json")
        return slug, "ok"
    except Exception as e:
        return slug, f"FAILED: {str(e)[:80]}"

if __name__ == "__main__":
    t0 = time.time()
    slugs = member_slugs()
    print(f"{len(slugs)} members found on BSP pages")
    with ThreadPoolExecutor(max_workers=3) as pool:
        for slug, status in pool.map(one, slugs):
            print(f"  {slug:<32} {status}")

    rows, domain_count = [], collections.Counter()
    for f in sorted(BASE.glob("profile_*.json")):
        r = json.loads(f.read_text())
        cl = r["claims"]
        facts = sum(c["type"] == "stated" for c in cl)
        offering = next((c["value"] for c in cl if c["field"] == "offering" and c["type"] == "stated"), "-")
        domain_count.update(r["domains"])
        rows.append((r["company_id"], ", ".join(r["domains"]) or "-", facts, offering))

    secs = time.time() - t0
    md = ["# Baseline profiles for all BSP members (member pages only)", "",
          f"{len(rows)} profiles in {secs/60:.1f} min. Source: bluesciencepark.se/medlem/<slug>/. "
          "Facts are quote-verified; these are baselines, not the enriched demo profiles.", "",
          "| Member | Domains | Facts | Offering |", "|---|---|---|---|"]
    md += [f"| {a} | {b} | {c} | {d} |" for a, b, c, d in rows]
    md += ["", "## Members per domain", ""] + [f"- {d}: {n}" for d, n in domain_count.most_common()]
    (BASE / "SUMMARY.md").write_text("\n".join(md))
    print(f"\nDONE: {len(rows)} baseline profiles in {secs/60:.1f} min -> {BASE / 'SUMMARY.md'}")
    print("Members per domain:", dict(domain_count.most_common()))
