"""Unit tests for the profiling pipeline (P1): no network, no LLM, no database."""
import uuid
import pytest
from pydantic import ValidationError

from pipeline.profiler import profiler as P
from pipeline.profiler import corroborate as C
from pipeline.common.models import ProfileClaim


def claim(field, value, type_="stated", verified=True, quote="q", url="https://example.com/"):
    return {"field": field, "value": value, "type": type_, "verified": verified,
            "quote": quote, "source_url": url}


# --- text normalisation -------------------------------------------------------
def test_norm_lowercases_and_collapses_whitespace():
    assert P.norm("  Wave   ENERGY\n converter ") == "wave energy converter"


def test_norm_unifies_typographic_quotes_and_dashes():
    assert P.norm("“Ocean” – power’s") == '"ocean" - power\'s'


def test_norm_handles_none():
    assert P.norm(None) == ""


# --- quote validator ----------------------------------------------------------
PAGE = P.norm("Ocean Harvesting develops InfinityWEC, a 500 kW point absorbing wave energy converter.")


def test_exact_quote_scores_100():
    assert P.quote_score("a 500 kW point absorbing wave energy converter", PAGE) == 100.0


def test_quote_with_typographic_differences_still_matches():
    assert P.quote_score("A 500 kW point   absorbing wave energy converter", PAGE) == 100.0


def test_invented_quote_scores_below_threshold():
    assert P.quote_score("offers offshore oil drilling services worldwide", PAGE) < P.VERIFY_MIN


def test_empty_quote_scores_zero():
    assert P.quote_score("", PAGE) == 0.0


# --- deterministic ids (idempotent loads) -------------------------------------
def test_claim_id_is_stable_across_runs():
    assert P.claim_id("oht", "offering", "Wave power") == P.claim_id("oht", "offering", "Wave power")


def test_claim_id_ignores_case_and_spacing():
    assert P.claim_id("oht", "offering", "Wave  Power") == P.claim_id("oht", "offering", "wave power")


def test_claim_id_differs_per_company_and_field():
    a = P.claim_id("oht", "offering", "Wave power")
    assert a != P.claim_id("addsecure", "offering", "Wave power")
    assert a != P.claim_id("oht", "technology", "Wave power")
    assert isinstance(a, uuid.UUID)


# --- dedupe and caps ----------------------------------------------------------
def test_dedupe_removes_near_identical_values():
    kept = P.dedupe([claim("offering", "Wave energy converter"),
                     claim("offering", "wave energy converter InfinityWEC")])
    assert len(kept) == 1


def test_dedupe_respects_field_cap():
    kept = P.dedupe([claim("size", "1-10"), claim("size", "11-50")])
    assert len(kept) == P.CAP["size"] == 1


def test_dedupe_prefers_verified_stated_over_inferred():
    kept = P.dedupe([claim("founded", "2007", type_="inferred", verified=False),
                     claim("founded", "2007", type_="stated", verified=True)])
    assert kept[0]["type"] == "stated" and kept[0]["verified"]


def test_dedupe_prefers_own_pages_over_old_news():
    kept = P.dedupe([
        claim("size", "1-10", url="https://www.bluesciencepark.se/aktuellt/old-article/"),
        claim("size", "1-10", url="https://www.bluesciencepark.se/medlem/ocean-harvesting/"),
    ])
    assert "/medlem/" in kept[0]["source_url"]


# --- LLM output robustness ----------------------------------------------------
def test_as_list_accepts_dict_list_and_junk():
    assert P.as_list({"topics": ["a"]}, "topics") == ["a"]
    assert P.as_list(["a", "b"], "topics") == ["a", "b"]
    assert P.as_list("unexpected", "topics") == []


def test_chunks_keep_all_text():
    text = "\n".join(f"line {i} " + "x" * 50 for i in range(200))
    parts = list(P.chunks(text, size=1000))
    assert len(parts) > 1
    assert "".join(parts).replace("\n", "") == text.replace("\n", "")


# --- schema contract ----------------------------------------------------------
def test_profile_claim_rejects_unknown_field():
    with pytest.raises(ValidationError):
        ProfileClaim(id=uuid.uuid4(), company_id="oht", field="salary", type="stated")


def test_profile_claim_defaults_are_safe():
    c = ProfileClaim(id=uuid.uuid4(), company_id="oht", field="offering", type="stated", value="x")
    assert c.origin == "agent" and c.verified is False and c.is_simulated is False


# --- corroboration helpers ----------------------------------------------------
def test_sentences_drop_fragments_and_split_on_punctuation():
    out = C.sentences("Too short. This sentence is clearly long enough to count! Another long enough sentence here.")
    assert out == ["This sentence is clearly long enough to count!", "Another long enough sentence here."]


def test_size_conflict_detected():
    docs = [{"hints": {"employees": ["275"]}}]
    assert C.size_conflict("200+", docs) is not None


def test_size_ranges_are_not_conflicts():
    docs = [{"hints": {"employees": ["1-10"]}}]
    assert C.size_conflict("1-10", docs) is None


def test_source_quality_order():
    assert C.QUALITY["company_website"] > C.QUALITY["bsp_member_page"] > C.QUALITY["bsp_news"]
