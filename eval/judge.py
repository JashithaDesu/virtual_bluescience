"""Hand-check each stated claim: y = correct, n = wrong, s = skip. Saves eval/results/judged_<slug>.json"""
import sys, json, pathlib
ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "pipeline/profiler/out"
RES = ROOT / "eval/results"
RES.mkdir(parents=True, exist_ok=True)

def judge(cid):
    claims = [c for c in json.loads((OUT / f"profile_{cid}.json").read_text())["claims"] if c["type"] == "stated"]
    marks = {}
    print(f"\n=== {cid}: {len(claims)} facts. Is the VALUE a correct reading of the QUOTE? (y/n/s)")
    for i, c in enumerate(claims, 1):
        print(f"\n[{i}/{len(claims)}] {c['field']}: {c['value']}\n   quote: \"{c['quote']}\"")
        a = ""
        while a not in ("y", "n", "s"):
            a = input("   correct? (y/n/s): ").strip().lower()
        marks[c["id"]] = a
    ok, bad = sum(v == "y" for v in marks.values()), sum(v == "n" for v in marks.values())
    acc = ok / (ok + bad) if ok + bad else None
    (RES / f"judged_{cid}.json").write_text(json.dumps({"company_id": cid, "correct": ok, "wrong": bad,
        "accuracy": acc, "marks": marks}, indent=2))
    print(f"\n{cid}: {ok} correct, {bad} wrong -> accuracy {acc:.0%}" if acc is not None else "no marks")

for cid in sys.argv[1:] or ["ocean-harvesting", "addsecure", "malvacom"]:
    judge(cid)
