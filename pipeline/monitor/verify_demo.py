from datetime import datetime

from pipeline.common import db
from pipeline.monitor.embed_companies import load_profile

COMPANIES = ["ocean-harvesting", "addsecure", "malvacom"]


def main():
    client = db.client()
    opportunities = {
        row["id"]: row
        for row in client.table("opportunities").select(
            "id,title,type,url,retrieved_at,date_or_deadline,"
            "next_step,eligibility,is_simulated"
        ).execute().data
    }
    top_fives = {}
    today = datetime.now().astimezone().date().isoformat()

    for company_id in COMPANIES:
        profile = load_profile(company_id)
        accepted_ids = {claim["id"] for claim in profile["claims"]}
        rows = (
            client.table("matches")
            .select("opportunity_id,score,rank,reason")
            .eq("company_id", company_id).order("rank").execute().data
        )
        assert rows, "No matches: " + company_id
        assert [row["rank"] for row in rows] == list(range(1, len(rows) + 1))
        assert len({row["opportunity_id"] for row in rows}) == len(rows)

        for row in rows:
            opportunity = opportunities[row["opportunity_id"]]
            assert opportunity["url"].startswith("https://")
            assert opportunity["retrieved_at"]
            assert opportunity["next_step"].strip()
            assert row["reason"].strip()
            assert any(
                f"[claim {claim_id}]" in row["reason"]
                for claim_id in accepted_ids
            ), "No accepted profile citation"
            deadline = opportunity["date_or_deadline"]
            assert not deadline or deadline >= today, "Expired opportunity"
            if opportunity["type"] == "funding":
                assert opportunity["eligibility"] == "potential"
                assert "Potential match only" in row["reason"]
            assert not opportunity["is_simulated"], "Unexpected simulated item"

        top_fives[company_id] = [row["opportunity_id"] for row in rows[:5]]
        print("\n" + company_id + f" — {len(rows)} verified matches")
        for row in rows[:5]:
            opportunity = opportunities[row["opportunity_id"]]
            print(
                f"{row['rank']}. [{opportunity['type']}] "
                f"{opportunity['title']}"
            )

    assert len({tuple(ids) for ids in top_fives.values()}) == 3
    print("\nPASS: distinct live feeds, sources, dates, next steps,")
    print("accepted claim citations, and potential-only funding labels.")


if __name__ == "__main__":
    main()
