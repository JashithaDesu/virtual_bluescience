"""Keep profiles current: re-fetch pages, compare content hashes, re-profile only changed companies.
--simulate-change <slug>: demo mode, adds a SIMULATED news sentence, shows the diff, restores, never writes to DB."""
import sys, json, hashlib, argparse, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from pipeline.profiler.member_page import parse_member
from pipeline.profiler.fetcher import fetch_page
from pipeline.profiler import profiler as P

HERE = pathlib.Path(__file__).parent
SIM_TEXT = (" Nyhet 2026: Ocean Harvesting öppnar en finansieringsrunda på 10 MSEK "
            "för att skala upp InfinityWEC.")

def cached_hash(path):
    return json.loads(path.read_text())["content_hash"] if path.exists() else None

def refresh_pages(cid, pages):
    changed = []
    mp = P.CACHE / f"member_{cid}.json"
    before = cached_hash(mp)
    after = parse_member(cid)["content_hash"]
    print(f"   member page   {'UNCHANGED' if before == after else 'CHANGED'}")
    if before != after:
        changed.append("member page")
    for url in pages:
        sp = P.CACHE / f"site_{cid}_{hashlib.md5(url.encode()).hexdigest()[:8]}.json"
        before = cached_hash(sp)
        rec = fetch_page(cid, url, set())
        if rec is None:
            print(f"   {url}  REJECTED now, kept previous version")
            continue
        state = "UNCHANGED" if before == rec["content_hash"] else "CHANGED"
        print(f"   {url}  {state}")
        if state == "CHANGED":
            changed.append(url)
    return changed

def diff(old, new):
    """Compare by meaning: same field + near-identical value = unchanged. Topics summarised in one line."""
    from rapidfuzz import fuzz
    same = lambda a, b: a["field"] == b["field"] and a["type"] == b["type"] and \
        fuzz.token_set_ratio(P.norm(a["value"] or "-"), P.norm(b["value"] or "-")) >= 85
    old_c = [c for c in (old["claims"] if old else []) if c["field"] != "relevant_topic"]
    new_c = [c for c in new["claims"] if c["field"] != "relevant_topic"]
    added = [c for c in new_c if not any(same(c, o) for o in old_c)]
    removed = [c for c in old_c if not any(same(c, n) for n in new_c)]
    fmt = lambda c: f"{c['type'].upper():<8} {c['field']}: {c['value'] or '-'}"
    for c in added:
        print(f"   + {fmt(c)}" + (f'   "{c["quote"][:60]}"' if c.get("quote") else ""))
    for c in removed:
        print(f"   - {fmt(c)}")
    if not added and not removed:
        print("   (no fact changes)")
    n_topics = sum(c["field"] == "relevant_topic" for c in new["claims"])
    print(f"   ~ {n_topics} opportunity topics re-derived from the updated facts")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("companies", nargs="*")
    ap.add_argument("--simulate-change", metavar="SLUG")
    ap.add_argument("--no-load", action="store_true")
    a = ap.parse_args()
    companies = json.loads((HERE / "companies.json").read_text())
    targets = [a.simulate_change] if a.simulate_change else (a.companies or list(companies))

    for cid in targets:
        name, pages = companies[cid]["name"], companies[cid]["pages"]
        out_file = P.OUT / f"profile_{cid}.json"
        prev_text = out_file.read_text() if out_file.exists() else None
        prev = json.loads(prev_text) if prev_text else None
        print(f"\n=== {cid}")
        changed = refresh_pages(cid, pages)

        member_file = P.CACHE / f"member_{cid}.json"
        original_member = None
        if a.simulate_change:
            original_member = member_file.read_text()
            m = json.loads(original_member)
            m["text"] += SIM_TEXT
            m["content_hash"] = hashlib.sha256(m["text"].encode()).hexdigest()
            member_file.write_text(json.dumps(m, ensure_ascii=False, indent=2))
            changed.append("member page (SIMULATED news sentence)")
            print("   member page   CHANGED (SIMULATED)")

        if not changed:
            print("   -> no changes: profile kept, 0 LLM calls")
            continue
        print(f"   -> {len(changed)} changed page(s): re-profiling")
        new = P.profile(cid, name)
        diff(prev, new)

        if a.simulate_change:
            member_file.write_text(original_member)
            if prev_text:
                out_file.write_text(prev_text)
            print("   (SIMULATED: cache and profile restored, nothing written to the database)")
        elif not a.no_load:
            from pipeline.profiler.load_profiles import load
            load(cid)

if __name__ == "__main__":
    main()
