"""Read-only integrity check for every match's profile-claim citations."""
import re
import sys
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pipeline.common import db

CITATION = re.compile(r"\[claim\s+([^\]]+)\]", re.IGNORECASE)


def main():
    client = db.client()
    matches = []
    offset = 0
    while True:
        page = (
            client.table("matches")
            .select("company_id,opportunity_id,reason")
            .order("company_id").order("opportunity_id")
            .range(offset, offset + 499).execute().data
        )
        matches.extend(page)
        if len(page) < 500:
            break
        offset += 500

    if not matches:
        raise SystemExit("FAIL: no matches available to check.")

    parsed = []
    claim_ids = set()
    for match in matches:
        tokens = CITATION.findall(match.get("reason") or "")
        ids = []
        errors = []
        if not tokens:
            errors.append("no claim citations")
        for token in tokens:
            try:
                claim_id = str(UUID(token.strip()))
                ids.append(claim_id)
                claim_ids.add(claim_id)
            except ValueError:
                errors.append("malformed claim UUID")
        parsed.append((match, ids, errors))

    claims = {}
    ordered_ids = sorted(claim_ids)
    for start in range(0, len(ordered_ids), 100):
        rows = (
            client.table("profile_claims").select("id,company_id")
            .in_("id", ordered_ids[start:start + 100]).execute().data
        )
        claims.update({str(UUID(row["id"])): row for row in rows})

    passed = failed = references = valid_references = 0
    missing = wrong_company = malformed = no_citations = 0

    for match, ids, errors in parsed:
        no_citations += "no claim citations" in errors
        malformed += errors.count("malformed claim UUID")
        for claim_id in ids:
            references += 1
            claim = claims.get(claim_id)
            if claim is None:
                missing += 1
                errors.append("missing claim " + claim_id)
            elif claim["company_id"] != match["company_id"]:
                wrong_company += 1
                errors.append("cross-company claim " + claim_id)
            else:
                valid_references += 1

        if errors:
            failed += 1
            print(
                "FAIL:",
                match["company_id"],
                "| opportunity:", match["opportunity_id"],
                "|", "; ".join(errors),
            )
        else:
            passed += 1

    print("\n=== REASON INTEGRITY ===")
    print("Matches checked:", len(matches))
    print("PASS:", passed)
    print("FAIL:", failed)
    print("Valid claim references:", valid_references, "/", references)
    print("Missing claims:", missing)
    print("Cross-company references:", wrong_company)
    print("Malformed references:", malformed)
    print("Matches without citations:", no_citations)
    print("Checks existence and ownership, not semantic correctness.")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
