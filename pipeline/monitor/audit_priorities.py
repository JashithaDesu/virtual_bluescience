from pipeline.common import db
from pipeline.monitor.embed_companies import load_profile

for company_id in ("ocean-harvesting", "addsecure", "malvacom"):
    profile = load_profile(company_id)
    accepted = {claim["id"] for claim in profile["claims"]}
    rows = (
        db.client().table("profile_claims")
        .select("id,value,type,confidence,origin,quote,source_url,retrieved_at")
        .eq("company_id", company_id)
        .eq("field", "priority")
        .execute().data
    )
    print("\nCOMPANY:", company_id)
    print("Private user priorities:", len(profile["priorities"]))
    if not rows:
        print("No priority claims.")
    for row in rows:
        print("\nID:", row["id"])
        print("Included in matching:", row["id"] in accepted)
        print("Value:", row["value"])
        print("Type:", row["type"], "| Confidence:", row["confidence"])
        print("Origin:", row["origin"])
        print("Quote:", row["quote"])
        print("Source:", row["source_url"])
        print("Retrieved:", row["retrieved_at"])
