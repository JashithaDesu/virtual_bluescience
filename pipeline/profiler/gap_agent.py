"""Gap-filling profiler agent: observe gaps -> search -> decide -> act (with guardrail) -> re-profile. Max 2 rounds."""
import re, sys, json, hashlib, datetime, argparse, pathlib
from urllib.parse import quote_plus
import httpx
from bs4 import BeautifulSoup

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from pipeline.common.llm import chat_json
from pipeline.profiler import profiler as P
from pipeline.profiler.refresh import diff

HERE = pathlib.Path(__file__).parent
UA = {"User-Agent": "Mozilla/5.0 VSP-hackathon-bot/0.1"}
MAX_ROUNDS, MAX_PAGES = 2, 3

SYSTEM_PLAN = """You are the planning step of a company-profiling agent.
Goal: fill MISSING fields in one company's profile using public news pages.
You get the company name, its missing fields, and candidate URLs (the topic is visible in the URL slug).
Choose at most 3 URLs that most likely contain information about THIS company for the missing fields.
Skip URLs that are about other companies or unrelated topics.
Return JSON: {"plan": [{"url": "...", "reason": "...", "fields": ["priority", ...]}],
              "skipped": [{"url": "...", "reason": "..."}]}
If nothing is useful, return an empty plan."""

def gaps(profile):
    return [c["field"] for c in profile["claims"] if c["type"] == "missing"]

def search_bsp(name):
    url = f"https://www.bluesciencepark.se/?s={quote_plus(name.lower())}"
    html = httpx.get(url, timeout=20, follow_redirects=True, headers=UA).text
    return sorted(set(re.findall(r'href="(https://www\.bluesciencepark\.se/aktuellt/[^"#]+)"', html)))

def fetch_article(cid, name, url):
    html = httpx.get(url, timeout=20, follow_redirects=True, headers=UA).text
    soup = BeautifulSoup(html, "html.parser")
    block = soup.find("div", attrs={"data-elementor-type": "single-post"}) or soup.find("main") or soup.body
    for t in block(["script", "style", "noscript", "svg", "form"]):
        t.decompose()
    text = re.sub(r"\s+", " ", block.get_text(" ", strip=True))
    key = P.norm(name)
    if key not in P.norm(text):
        return None, f"guardrail: page does not mention '{name}'"
    rec = {"company_id": cid, "source_url": url, "source_type": "bsp_news",
           "retrieved_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
           "content_hash": hashlib.sha256(text.encode()).hexdigest(), "chars": len(text), "text": text}
    (P.CACHE / f"news_{cid}_{hashlib.md5(url.encode()).hexdigest()[:8]}.json").write_text(
        json.dumps(rec, ensure_ascii=False, indent=2))
    return rec, f"fetched {len(text)} chars"

def run(cid, load=False):
    companies = json.loads((HERE / "companies.json").read_text())
    name = companies[cid]["name"]
    profile = json.loads((P.OUT / f"profile_{cid}.json").read_text())
    used = {json.loads(f.read_text())["source_url"] for f in P.CACHE.glob(f"news_{cid}_*.json")}
    log = {"company_id": cid, "started": datetime.datetime.now().isoformat(), "rounds": []}
    print(f"\n=== GAP AGENT: {name}")

    for rnd in range(1, MAX_ROUNDS + 1):
        g = gaps(profile)
        print(f"\n[round {rnd}] OBSERVE  missing fields: {g or 'none'}")
        if not g:
            log["stop"] = "no gaps left"; break
        cands = [u for u in search_bsp(name) if u not in used]
        print(f"[round {rnd}] SEARCH   {len(cands)} new candidate pages")
        if not cands:
            log["stop"] = "no new candidates"; break
        user = f"Company: {name}\nMissing fields: {', '.join(g)}\nCandidate URLs:\n" + "\n".join(cands)
        decision = chat_json(SYSTEM_PLAN, user)
        plan = [p for p in decision.get("plan", []) if p.get("url") in cands][:MAX_PAGES]
        for s in decision.get("skipped", [])[:6]:
            print(f"[round {rnd}] SKIP     {s.get('url', '')[-60:]}  ({s.get('reason', '')[:70]})")
        if not plan:
            print(f"[round {rnd}] DECIDE   nothing useful -> stop")
            log["rounds"].append({"round": rnd, "gaps": g, "decision": decision}); log["stop"] = "no useful pages"; break
        acts = []
        for p in plan:
            print(f"[round {rnd}] DECIDE   read {p['url'][-60:]}\n                    because: {p.get('reason', '')[:100]}")
            try:
                rec, status = fetch_article(cid, name, p["url"])
            except Exception as e:
                rec, status = None, f"fetch failed ({type(e).__name__}), skipped"
            used.add(p["url"])
            print(f"[round {rnd}] ACT      {status}")
            acts.append({"url": p["url"], "reason": p.get("reason"), "status": status})
        before = profile
        profile = P.profile(cid, name)
        print(f"[round {rnd}] UPDATE   fact changes:")
        diff(before, profile)
        log["rounds"].append({"round": rnd, "gaps": g, "decision": decision, "actions": acts,
                              "gaps_after": gaps(profile)})
    else:
        log["stop"] = "round budget used"

    print(f"\nSTOP: {log.get('stop')}. Remaining gaps: {gaps(profile) or 'none'}")
    (P.OUT / f"agent_log_{cid}.json").write_text(json.dumps(log, ensure_ascii=False, indent=2))
    if load:
        from pipeline.profiler.load_profiles import load as load_db
        load_db(cid)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("company")
    ap.add_argument("--load", action="store_true", help="write the updated profile to Supabase")
    a = ap.parse_args()
    run(a.company, a.load)
