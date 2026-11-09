"""Score a token snapshot using fee.json; no network calls or trading actions."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Mapping


class ScoringInputError(ValueError):
    """Raised when input fields have invalid types or values."""


INPUT_FIELDS = (
    "age_hours",
    "market_cap_usd",
    "volume_24h_usd",
    "liquidity_usd",
    "fee_24h_usd",
    "cr10_pct",
    "holder_growth_24h_pct",
    "price_action",
)


def _default_config_path() -> Path:
    candidates = (Path.cwd() / "fee.json", Path(__file__).resolve().parents[2] / "fee.json")
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise FileNotFoundError("fee.json not found; pass config_path or run from the repository root")


def load_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """Load scoring configuration from fee.json."""
    path = Path(config_path) if config_path is not None else _default_config_path()
    with path.open(encoding="utf-8") as handle:
        config = json.load(handle)
    if not isinstance(config, dict) or "scoring" not in config:
        raise ValueError(f"Invalid scoring configuration: {path}")
    return config


def _number(value: Any, field: str) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        raise ScoringInputError(f"{field} must be a number, not a boolean")
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ScoringInputError(f"{field} must be numeric") from error
    if not math.isfinite(number):
        raise ScoringInputError(f"{field} must be finite")
    if field != "holder_growth_24h_pct" and number < 0:
        raise ScoringInputError(f"{field} cannot be negative")
    return number


def _band_points(value: float, bands: list[dict[str, Any]]) -> float:
    for band in bands:
        lower, upper = band.get("min"), band.get("max")
        if (lower is None or value >= lower) and (upper is None or value < upper):
            return float(band["points"])
    raise ValueError(f"No scoring band configured for value {value}")


def _component(name: str, points: float | None, maximum: float) -> dict[str, float | None]:
    return {"points": points, "max_points": maximum}


def evaluate_token(metrics: Mapping[str, Any], config: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Evaluate one point-in-time snapshot. All percentage inputs use percentage units.

    Required fields are listed in fee.json's input_schema. Missing inputs produce an
    incomplete result and never silently count as zero. Ratios are derived here so
    callers cannot accidentally pass ratio fractions where percentages are expected.
    """
    cfg = dict(config) if config is not None else load_config()
    criteria = cfg["criteria"]["basic_requirements"]
    fee_criteria = cfg["criteria"]["fee_and_volume"]
    scoring = cfg["scoring"]
    rubric = scoring["rubric"]
    hard = rubric["hard_filters"]
    weights = scoring["breakdown"]

    values: dict[str, float | None] = {
        field: _number(metrics.get(field), field)
        for field in INPUT_FIELDS if field != "price_action"
    }
    raw_action = metrics.get("price_action")
    action = str(raw_action).strip().lower() if raw_action is not None and str(raw_action).strip() else None

    missing = [field for field in INPUT_FIELDS if values.get(field) is None] if action is None else [
        field for field in INPUT_FIELDS if field != "price_action" and values.get(field) is None
    ]
    if action is not None and action not in rubric["price_action_points"]:
        missing.append("price_action (unknown value)")

    age = values["age_hours"]
    market_cap = values["market_cap_usd"]
    volume = values["volume_24h_usd"]
    liquidity = values["liquidity_usd"]
    fee = values["fee_24h_usd"]
    cr10 = values["cr10_pct"]
    growth = values["holder_growth_24h_pct"]

    ratios: dict[str, float | None] = {
        "volume_to_mc_pct": volume / market_cap * 100 if volume is not None and market_cap and market_cap > 0 else None,
        "liquidity_to_mc_pct": liquidity / market_cap * 100 if liquidity is not None and market_cap and market_cap > 0 else None,
        "fee_to_volume_pct": fee / volume * 100 if fee is not None and volume and volume > 0 else None,
        "volume_to_liquidity": volume / liquidity if volume is not None and liquidity and liquidity > 0 else None,
    }

    rejects: list[str] = []
    warnings: list[str] = []
    if age is not None and age < hard["min_age_hours"]:
        rejects.append(f"Token age {age:g}h is below {hard['min_age_hours']}h")
    if market_cap is not None and not hard["market_cap_min_usd"] <= market_cap <= hard["market_cap_max_usd"]:
        rejects.append("Market cap is outside the configured range")
    if liquidity is not None and liquidity < hard["liquidity_min_usd"]:
        rejects.append(f"Liquidity is below ${hard['liquidity_min_usd']:,.0f}")
    if ratios["liquidity_to_mc_pct"] is not None and ratios["liquidity_to_mc_pct"] < hard["liquidity_to_mc_min_pct"]:
        rejects.append(f"Liquidity/MC is below {hard['liquidity_to_mc_min_pct']}%")
    vmc = ratios["volume_to_mc_pct"]
    if vmc is not None and (vmc < hard["volume_to_mc_min_pct"] or vmc > hard["volume_to_mc_max_pct"]):
        rejects.append("Volume/MC is outside hard-filter limits")
    fee_ratio = ratios["fee_to_volume_pct"]
    if fee_ratio is not None and (fee_ratio < hard["fee_to_volume_min_pct"] or fee_ratio > hard["fee_to_volume_max_pct"]):
        rejects.append("Fee/volume is outside hard-filter limits")
    vl = ratios["volume_to_liquidity"]
    if vl is not None and vl > hard["volume_to_liquidity_max"]:
        rejects.append("Volume/liquidity exceeds the hard-filter limit")

    components: dict[str, dict[str, float | None]] = {}
    def add(name: str, points: float | None) -> None:
        components[name] = _component(name, points, float(weights[name]))

    add("volume_to_mc_in_range", _band_points(vmc, rubric["volume_to_mc_pct"]) if vmc is not None else None)
    add("liquidity_to_mc", _band_points(ratios["liquidity_to_mc_pct"], rubric["liquidity_to_mc_pct"]) if ratios["liquidity_to_mc_pct"] is not None else None)
    add("fee_to_volume_correct_and_stable", _band_points(fee_ratio, rubric["fee_to_volume_pct"]) if fee_ratio is not None else None)
    add("volume_to_liquidity", _band_points(vl, rubric["volume_to_liquidity"]) if vl is not None else None)
    if cr10 is not None and growth is not None:
        holder_points = _band_points(cr10, rubric["cr10_pct"]) + _band_points(growth, rubric["holder_growth_24h_pct"])
        add("holder_and_cr10", holder_points)
    else:
        add("holder_and_cr10", None)
    action_points = rubric["price_action_points"].get(action) if action is not None else None
    add("price_action", float(action_points) if action_points is not None else None)

    earned = sum(float(item["points"]) for item in components.values() if item["points"] is not None)
    available = sum(float(item["max_points"]) for item in components.values() if item["points"] is not None)

    if vmc is not None and not 5 <= vmc <= 30:
        warnings.append("Volume/MC is outside the ideal 5–30% band")
    if ratios["liquidity_to_mc_pct"] is not None and ratios["liquidity_to_mc_pct"] < 8:
        warnings.append("Liquidity/MC is below the preferred 8% level")
    if vl is not None and not 0.5 <= vl <= 2:
        warnings.append("Volume/liquidity is outside the ideal 0.5x–2.0x band")
    if growth is not None and growth > 5:
        warnings.append("Holder growth is unusually rapid; check for wallet churn or measurement artifacts")
    if action == "breakdown":
        warnings.append("Price action is marked as breakdown")

    pool_tier = _number(metrics.get("pool_fee_tier_pct"), "pool_fee_tier_pct")
    tolerance = fee_criteria["fee_to_volume_24h"].get("pool_tier_comparison_tolerance_percentage_points", 0.2)
    if pool_tier is not None and fee_ratio is not None and abs(pool_tier - fee_ratio) > tolerance:
        warnings.append("Observed fee/volume differs from the supplied nominal pool fee tier; verify definitions and data source")

    if rejects:
        status = "reject"
    elif missing:
        status = "incomplete"
    elif earned >= scoring["pass_threshold"]:
        status = "pass"
    elif earned >= scoring.get("warn_threshold", 0):
        status = "warn"
    else:
        status = "fail"

    return {
        "score": round(earned, 2),
        "score_out_of": int(scoring["total"]),
        "available_points": round(available, 2),
        "pass": status == "pass",
        "status": status,
        "missing_fields": missing,
        "reject_reasons": rejects,
        "warnings": warnings,
        "components": components,
        "metrics": {**values, "price_action": action, **ratios},
    }
