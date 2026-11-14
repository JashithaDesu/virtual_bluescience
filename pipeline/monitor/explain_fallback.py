"""LLM explanations with an uncached, same-company template fallback."""
import json
import os
import re
from contextvars import ContextVar
from pipeline.monitor.structured_log import event

EXPLANATION_MODE = ContextVar("explanation_mode", default="llm")

from pipeline.common.llm import chat_json as llm_chat_json

STOP = {
    "the", "and", "for", "with", "your", "our", "from", "that",
    "this", "into", "company", "companies", "support", "development",
}


def words(text):
    return {
        token for token in re.findall(r"[a-z0-9]+", text.lower())
        if len(token) > 2 and token not in STOP
    }


def template_response(user):
    payload = json.loads(user)
    claims = [
        claim for claim in payload["accepted_claims"]
        if claim.get("id")
        and claim.get("type") != "missing"
        and str(claim.get("value") or "").strip()
    ]
    if not claims:
        raise ValueError("No accepted company claims for safe fallback")

    items = []
    for match in payload["matches"]:
        opportunity = match["opportunity"]
        context = words(
            opportunity["title"] + " " + opportunity["summary"]
        )

        def relevance(claim):
            overlap = len(context & words(claim["value"]))
            concrete = claim["field"] in {
                "offering", "technology", "application_area", "expertise"
            }
            return overlap, concrete, claim["type"] == "stated"

        claim = max(claims, key=relevance)
        label = (
            "user-provided " if claim.get("origin") == "user"
            else "inferred interest — " if claim["type"] == "inferred"
            else ""
        )
        reason = (
            f'Matches your {label}{claim["field"]}: {claim["value"]} '
            f'[claim {claim["id"]}]. '
            f'Potential relevance to {opportunity["title"]}; '
            "confirm scope, requirements and current availability."
        )
        if opportunity["type"] == "funding":
            reason += " Eligibility is unconfirmed; consult BSP staff."
        items.append({
            "opportunity_id": opportunity["id"],
            "reason": reason,
            "claim_ids": [claim["id"]],
        })
    return {"items": items}


def chat_json(system, user, **kwargs):
    EXPLANATION_MODE.set("llm")
    # One attempt: quota failures must not block demo reranking for minutes.
    kwargs["retries"] = 1
    if os.getenv("P2_EXPLAIN_NO_CACHE") == "1":
        kwargs["use_cache"] = False
    try:
        return llm_chat_json(system, user, **kwargs)
    except Exception as exc:
        EXPLANATION_MODE.set("template")
        event("explanation_fallback", reason="template",
              error_type=type(exc).__name__)
        return template_response(user)
