"""api/guard.py · P3 · rule layer of the /ask guard (pure functions, unit-tested).
Runs BEFORE the LLM: overrides, cross-company requests and eligibility never depend on the model."""
import re

OVERRIDE = [
    r"ignore (all |any |your |the |previous |prior |above )*(instructions|rules|prompts?)",
    r"system prompt", r"\bpretend\b", r"\bact as\b", r"you are now", r"from now on,? you",
    r"role ?-?play", r"jailbreak", r"developer mode", r"forget (your|all|the|previous)",
    r"(reveal|show|print|repeat) (me )?(your|the) (prompt|instructions|rules)",
    r"disregard (your|the|all)", r"new (role|persona)",
]
PRIVATE_WORDS = r"(priorit|correction|note|match|chat|conversation|feedback|saved|private|rejected|internal|secret|edit)"
ELIGIBILITY = [
    r"\b(are we|am i|is (my|our) company|are they) eligible\b", r"\bguarantee", r"\bapprove (our|my|us|the)\b",
    r"\bcommit(ment)? to\b", r"\bpromise\b", r"\bwill (bsp|blue science park|you) (fund|pay|sponsor)\b",
    r"\bsign (a|the|our) (contract|agreement)\b", r"\blegal advice\b",
]

def mentioned_companies(text, companies, own_id):
    t = text.lower()
    hits = []
    for c in companies:
        if c["id"] == own_id:
            continue
        names = {c["id"].lower(), c["id"].replace("-", " ").lower(), (c.get("name") or "").lower()}
        if any(n and len(n) >= 4 and n in t for n in names):
            hits.append(c["id"])
    return hits

def rule_route(question, history, companies, own_id):
    """Returns (route, reason, other_company_ids). route None = let the LLM classify."""
    q = question.lower()
    recent = " ".join(h.lower() for h in history[-4:])
    if any(re.search(p, q) for p in OVERRIDE):
        return "refused", "override or role switch", []
    others = mentioned_companies(question, companies, own_id)
    if others and re.search(PRIVATE_WORDS, q):
        return "refused", "another company's non-public data", others
    if not others and re.search(r"\b(their|they|them|that company)\b", q) and re.search(PRIVATE_WORDS, q):
        prev = mentioned_companies(recent, companies, own_id)
        if prev:
            return "refused", "follow-up asks for another company's non-public data", prev
    if any(re.search(p, q) for p in ELIGIBILITY):
        return "refer_to_staff", "eligibility decision or commitment", others
    return None, "", others
