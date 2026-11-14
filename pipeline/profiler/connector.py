"""Connector agent (FILES ONLY): suggests potential collaborations between members, with an evidence basis.
Embeds profile facts (GPU if available) -> candidates -> LLM explains basis -> guardrail checks cited facts."""
import sys, json, pathlib, collections
import numpy as np
from rapidfuzz import fuzz

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from pipeline.common.llm import chat_json
from pipeline.profiler import profiler as P

OUT = P.OUT / "connections"
OUT.mkdir(parents=True, exist_ok=True)
DEMO = ["ocean-harvesting", "addsecure", "malvacom"]
FIELDS = ("offering", "technology", "expertise", "application_area", "market", "customer_group", "domain", "priority")

SYSTEM = """You suggest POTENTIAL collaborations between Blue Science Park member companies.
You get company A's facts and several candidate companies' facts (all from public pages).
Pick at most 3 candidates where a collaboration is plausible (complementary offerings, shared market,
one's technology fits the other's need). For each, give:
- "partner": the candidate id exactly as given
- "basis_a": ONE fact of company A copied exactly from its list
- "basis_b": ONE fact of the partner copied exactly from its list
- "why": one sentence on why they could work together, phrased as a possibility
- "confidence": "high" | "medium" | "low"
Never claim either company is interested or has agreed to anything. If no candidate fits, return an empty list.
Return JSON: {"suggestions": [...]}"""

def load_profiles():
    profs = {}
    for f in list(P.OUT.glob("profile_*.json")) + list((P.OUT / "baseline").glob("profile_*.json")):
        r = json.loads(f.read_text())
        facts = [c["value"] for c in r["claims"] if c["type"] == "stated" and c["field"] in FIELDS and c["value"]]
        if facts:
            all_facts = [c["value"] for c in r["claims"] if c["type"] == "stated" and c["value"]]
            profs[r["company_id"]] = {"name": r.get("name") or r["company_id"], "facts": facts, "all": all_facts,
                                      "domains": r.get("domains", [])}
    return profs

def embed(texts):
    from sentence_transformers import SentenceTransformer
    import torch
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2", device=dev)
    print(f"embedding {len(texts)} profiles on {dev}")
    return model.encode(texts, normalize_embeddings=True, batch_size=64, show_progress_bar=False)

def supported(text, facts):
    return any(fuzz.token_set_ratio(P.norm(text), P.norm(f)) >= 85 for f in facts)

def main():
    profs = load_profiles()
    ids = sorted(profs)
    vec = embed(["; ".join(profs[i]["facts"]) for i in ids])
    sim = vec @ vec.T
    idx = {c: n for n, c in enumerate(ids)}

    results, md = {}, ["# Potential connections (Connector agent, files only)", "",
                       "Basis = one public fact from each company. These are possibilities, not expressed interest.", ""]
    for a in DEMO:
        if a not in idx:
            continue
        order = np.argsort(-sim[idx[a]])
        cands = [ids[j] for j in order if ids[j] != a][:6]
        user = f"Company A: {a}\nFacts:\n" + "\n".join(f"- {f}" for f in profs[a]["facts"])
        for c in cands:
            user += f"\n\nCandidate: {c}\nFacts:\n" + "\n".join(f"- {f}" for f in profs[c]["facts"][:12])
        res = chat_json(SYSTEM, user)
        sugg = res.get("suggestions", []) if isinstance(res, dict) else res
        kept, dropped = [], 0
        for s in sugg:
            b = s.get("partner")
            if b in cands and supported(s.get("basis_a", ""), profs[a]["facts"]) and supported(s.get("basis_b", ""), profs[b]["facts"]):
                s["similarity"] = round(float(sim[idx[a], idx[b]]), 3)
                key = P.norm(b.replace("-", " "))
                s["already_connected"] = any(key in P.norm(f) for f in profs[a]["all"]) or \
                    any(P.norm(a.replace("-", " ")) in P.norm(f) for f in profs[b]["all"])
                kept.append(s)
            else:
                dropped += 1
        results[a] = {"candidates": cands, "suggestions": kept, "dropped_by_guardrail": dropped}
        md += [f"## {a}", f"Candidates considered (by profile similarity): {', '.join(cands)}", ""]
        for s in kept:
            tag = " - ALREADY CONNECTED (public), not a new suggestion" if s.get("already_connected") else ""
            md += [f"- **{s['partner']}** ({s['confidence']}, similarity {s['similarity']}){tag}",
                   f"  - {a}: {s['basis_a']}", f"  - {s['partner']}: {s['basis_b']}", f"  - Why: {s['why']}"]
        md += [f"- Dropped by guardrail (unsupported basis): {dropped}", ""]

    pairs = sorted(((float(sim[i, j]), ids[i], ids[j]) for i in range(len(ids)) for j in range(i + 1, len(ids))), reverse=True)[:10]
    md += ["## Staff view: members with similar profiles (shared interests, not necessarily partners)", ""]
    md += [f"- {a} <-> {b}  (similarity {s:.2f})" for s, a, b in pairs]
    (OUT / "connections.json").write_text(json.dumps({"by_company": results, "top_pairs": pairs}, ensure_ascii=False, indent=2))
    (OUT / "CONNECTIONS.md").write_text("\n".join(md))
    print("\n".join(md))

if __name__ == "__main__":
    main()
