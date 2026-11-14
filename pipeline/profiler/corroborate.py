"""Corroborate profile facts across all cached sources and score them 0-100.
score = 40 agreement + 25 source quality + 20 recency + 15 no-conflict.
Dry run by default; --apply updates confidence (high/medium/low) in the DB. Claim ids never change."""
import re, sys, json, pathlib, datetime, argparse, collections
import numpy as np
ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from pipeline.common import db
from pipeline.profiler import profiler as P
from pipeline.profiler.date_news_claims import published

FIELDS = {"offering", "technology", "expertise", "application_area", "market", "customer_group",
          "geography", "priority", "collaboration", "location", "founded", "size"}
QUALITY = {"company_website": 1.0, "bsp_member_page": 0.9, "bsp_news": 0.7}
SIM_MIN = 0.62
STALE_YEARS = 3
NOW = datetime.date.today()

def sentences(text):
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [s.strip() for s in parts if 15 <= len(s.strip()) <= 400]

def model():
    from sentence_transformers import SentenceTransformer
    import torch
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    return SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2", device=dev)

def load_docs(cid):
    docs = []
    files = sorted(P.CACHE.glob(f"member_{cid}.json")) + sorted(P.CACHE.glob(f"site_{cid}_*.json")) + \
            sorted(P.CACHE.glob(f"news_{cid}_*.json"))
    for f in files:
        d = json.loads(f.read_text())
        st = d.get("source_type") or ("bsp_member_page" if f.name.startswith("member_") else "company_website")
        age, year = 0.0, None
        if st == "bsp_news":
            pub = published(d["source_url"])
            if pub:
                year = pub[0]
                age = max(0.0, (NOW.year - pub[0]) + (NOW.month - pub[1]) / 12)
        docs.append({"url": d["source_url"], "type": st, "age": age,
                     "sents": sentences(d["text"]), "hints": d.get("hints", {}), "year": year})
    return docs

def size_conflict(value, docs):
    v = re.sub(r"\D", " ", value or "").split()
    for d in docs:
        for emp in d["hints"].get("employees", []):
            nums = re.findall(r"\d+", emp)
            if nums and "-" not in emp and not any(n in v for n in nums):
                return f"member-page field says {emp}"
    return None

def src_label(d):
    name = d["type"].replace("bsp_", "").replace("company_", "")
    return name if not d.get("year") else f"{name}({d['year']})"

def run(cid, m, apply):
    docs = load_docs(cid)
    for d in docs:
        d["vecs"] = m.encode(d["sents"], normalize_embeddings=True, show_progress_bar=False) if d["sents"] else None
    rows = db.client().table("profile_claims").select("id,field,value,type,confidence,source_url,origin") \
        .eq("company_id", cid).eq("type", "stated").eq("origin", "agent").execute().data
    rows = [r for r in rows if r["field"] in FIELDS and r["value"]]
    out = []
    for r in rows:
        base = r["value"].split(" (BSP news")[0]
        qv = m.encode([base], normalize_embeddings=True, show_progress_bar=False)[0]
        support = []
        for d in docs:
            sim = float(np.max(d["vecs"] @ qv)) if d["vecs"] is not None else 0.0
            if d["url"] == r["source_url"] or sim >= SIM_MIN:
                support.append(d)
        n = len({d["url"] for d in support})
        agreement = min(n, 3) / 3
        quality = max((QUALITY.get(d["type"], 0.5) for d in support), default=0.5)
        newest_age = min((d["age"] for d in support), default=5)
        recency = max(0.0, 1 - newest_age / 5)
        conflict = size_conflict(r["value"], docs) if r["field"] == "size" else None
        score = round(40 * agreement + 25 * quality + 20 * recency + (0 if conflict else 15))
        label = "CONFIRMED" if score >= 75 else "PLAUSIBLE" if score >= 50 else "WEAK/STALE"
        conf = "high" if score >= 75 else "medium" if score >= 50 else "low"
        live = any(d["age"] == 0 for d in support)
        if not live and newest_age >= STALE_YEARS:
            score, label, conf = min(score, 49), "STALE", "low"
        out.append({"id": r["id"], "field": r["field"], "value": r["value"], "score": score, "label": label,
                    "sources": n, "supported_by": ", ".join(src_label(d) for d in support), "conflict": conflict,
                    "old_confidence": r["confidence"], "new_confidence": conf})
        if apply and conf != r["confidence"]:
            db.client().table("profile_claims").update({"confidence": conf}).eq("id", r["id"]).execute()
    out.sort(key=lambda x: x["score"])
    print(f"\n=== {cid}: {len(out)} facts, {len(docs)} sources")
    for o in out:
        c = f"  CONFLICT: {o['conflict']}" if o["conflict"] else ""
        print(f"  {o['score']:>3} {o['label']:<10} {o['field']:<15} {o['value'][:55]:<55} "
              f"[{o['sources']} src: {o['supported_by']}]{c}")
    return out

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("companies", nargs="*", default=["ocean-harvesting", "addsecure", "malvacom"])
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    m = model()
    report = {cid: run(cid, m, a.apply) for cid in a.companies}
    outdir = P.OUT / "corroboration"
    outdir.mkdir(exist_ok=True)
    (outdir / "corroboration.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    counts = collections.Counter(o["label"] for v in report.values() for o in v)
    print(f"\nSUMMARY: {dict(counts)}  ({'APPLIED to DB' if a.apply else 'dry run, nothing changed'})")
