import json
from pathlib import Path

import pytest

from chuan.scorer import ScoringInputError, evaluate_token, load_config

ROOT = Path(__file__).resolve().parents[1]
CONFIG = load_config(ROOT / "fee.json")


def strong_token(**overrides):
    token = {
        "age_hours": 72,
        "market_cap_usd": 800_000,
        "volume_24h_usd": 144_000,
        "liquidity_usd": 96_000,
        "fee_24h_usd": 792,
        "cr10_pct": 28,
        "holder_growth_24h_pct": 1.5,
        "price_action": "consolidation",
    }
    token.update(overrides)
    return token


def test_strong_snapshot_passes_and_components_sum_to_100():
    result = evaluate_token(strong_token(), CONFIG)
    assert result["status"] == "pass"
    assert result["score"] == 100
    assert sum(part["points"] for part in result["components"].values()) == 100
    assert result["metrics"]["volume_to_mc_pct"] == pytest.approx(18)
    assert result["metrics"]["fee_to_volume_pct"] == pytest.approx(0.55)


def test_rejects_underage_token():
    result = evaluate_token(strong_token(age_hours=47), CONFIG)
    assert result["status"] == "reject"
    assert result["reject_reasons"]


@pytest.mark.parametrize("vmc,expected", [(1.99, "reject"), (2, "fail"), (4.99, "fail"), (5, "pass"), (30, "pass"), (50, "fail"), (80, "fail"), (80.01, "reject")])
def test_vmc_boundaries(vmc, expected):
    result = evaluate_token(strong_token(volume_24h_usd=800_000 * vmc / 100), CONFIG)
    assert result["status"] == expected


def test_fee_ratio_reject_limits_and_warning_band():
    below = evaluate_token(strong_token(fee_24h_usd=144_000 * 0.149 / 100), CONFIG)
    edge = evaluate_token(strong_token(fee_24h_usd=144_000 * 0.20 / 100), CONFIG)
    above = evaluate_token(strong_token(fee_24h_usd=144_000 * 1.51 / 100), CONFIG)
    assert below["status"] == "reject"
    assert edge["components"]["fee_to_volume_correct_and_stable"]["points"] == 8
    assert above["status"] == "reject"


def test_volume_liquidity_intermediate_band_and_reject():
    # 2.5x is acceptable-but-not-ideal and gets a defined partial score.
    result = evaluate_token(strong_token(volume_24h_usd=240_000), CONFIG)
    assert result["components"]["volume_to_liquidity"]["points"] == 8
    rejected = evaluate_token(strong_token(volume_24h_usd=500_000), CONFIG)
    assert rejected["status"] == "reject"


def test_holder_and_price_action_scores_are_defined():
    result = evaluate_token(strong_token(cr10_pct=50, holder_growth_24h_pct=-1, price_action="weak"), CONFIG)
    assert result["components"]["holder_and_cr10"]["points"] == 2
    assert result["components"]["price_action"]["points"] == 3


def test_missing_fields_are_incomplete_not_silently_zeroed():
    token = strong_token()
    del token["cr10_pct"]
    result = evaluate_token(token, CONFIG)
    assert result["status"] == "incomplete"
    assert result["pass"] is False
    assert "cr10_pct" in result["missing_fields"]
    assert result["available_points"] < 100


def test_invalid_negative_metric_is_rejected_as_input_error():
    with pytest.raises(ScoringInputError):
        evaluate_token(strong_token(liquidity_usd=-1), CONFIG)


def test_unknown_price_action_is_incomplete():
    result = evaluate_token(strong_token(price_action="pump"), CONFIG)
    assert result["status"] == "incomplete"
    assert any("price_action" in field for field in result["missing_fields"])


def test_fee_tier_mismatch_is_a_warning_only():
    result = evaluate_token(strong_token(pool_fee_tier_pct=0.25), CONFIG)
    assert result["status"] == "pass"
    assert any("nominal pool fee tier" in warning for warning in result["warnings"])


def test_config_is_valid_json_and_weights_total_100():
    raw = json.loads((ROOT / "fee.json").read_text(encoding="utf-8"))
    assert sum(raw["scoring"]["breakdown"].values()) == raw["scoring"]["total"]
