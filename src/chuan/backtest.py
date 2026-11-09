"""Offline CSV evaluation of fixed scoring criteria against forward returns.

This evaluates a pre-built dataset; it does not fetch prices or make trading decisions.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

from chuan.scorer import evaluate_token, load_config

FEATURE_COLUMNS = (
    "age_hours", "market_cap_usd", "volume_24h_usd", "liquidity_usd",
    "fee_24h_usd", "cr10_pct", "holder_growth_24h_pct", "price_action",
)


def _parse_time(value: str, row_number: int) -> datetime:
    try:
        return datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except (ValueError, AttributeError) as error:
        raise ValueError(f"row {row_number}: timestamp must be ISO-8601") from error


def _summarize(items: list[dict[str, Any]], positive_return_pct: float) -> dict[str, Any]:
    if not items:
        return {"count": 0, "hit_rate_pct": None, "mean_forward_return_pct": None, "median_forward_return_pct": None}
    returns = [item["forward_return_pct"] for item in items]
    hits = sum(value >= positive_return_pct for value in returns)
    return {
        "count": len(items),
        "hit_rate_pct": round(hits / len(items) * 100, 2),
        "mean_forward_return_pct": round(statistics.fmean(returns), 2),
        "median_forward_return_pct": round(statistics.median(returns), 2),
    }


def run_backtest(input_path: str | Path, config: dict[str, Any], return_column: str = "forward_7d_return_pct", positive_return_pct: float = 20.0) -> dict[str, Any]:
    path = Path(input_path)
    with path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        required = {"token", "timestamp", return_column, *FEATURE_COLUMNS}
        missing = sorted(required - set(reader.fieldnames or []))
        if missing:
            raise ValueError("CSV missing required columns: " + ", ".join(missing))
        evaluated: list[dict[str, Any]] = []
        for row_number, row in enumerate(reader, start=2):
            snapshot_time = _parse_time(row["timestamp"], row_number)
            try:
                forward_return = float(row[return_column])
            except (TypeError, ValueError) as error:
                raise ValueError(f"row {row_number}: {return_column} must be numeric") from error
            if not math.isfinite(forward_return):
                raise ValueError(f"row {row_number}: {return_column} must be finite")
            metrics: dict[str, Any] = {field: row[field] for field in FEATURE_COLUMNS}
            result = evaluate_token(metrics, config)
            evaluated.append({
                "token": row["token"],
                "timestamp": snapshot_time.isoformat(),
                "month": snapshot_time.strftime("%Y-%m"),
                "forward_return_pct": forward_return,
                "score": result["score"],
                "status": result["status"],
                "passed": result["pass"],
                "warnings": result["warnings"],
                "reject_reasons": result["reject_reasons"],
                "metrics": result["metrics"],
            })

    evaluated.sort(key=lambda item: item["timestamp"])
    pass_items = [item for item in evaluated if item["passed"]]
    other_items = [item for item in evaluated if not item["passed"]]
    monthly: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in evaluated:
        monthly[item["month"]].append(item)
    return {
        "rows": len(evaluated),
        "return_column": return_column,
        "positive_return_threshold_pct": positive_return_pct,
        "pass_cohort": _summarize(pass_items, positive_return_pct),
        "non_pass_cohort": _summarize(other_items, positive_return_pct),
        "status_counts": {status: sum(item["status"] == status for item in evaluated) for status in ("pass", "warn", "fail", "reject", "incomplete")},
        "by_snapshot_month": {
            month: {
                "all": _summarize(items, positive_return_pct),
                "pass": _summarize([item for item in items if item["passed"]], positive_return_pct),
                "non_pass": _summarize([item for item in items if not item["passed"]], positive_return_pct),
            }
            for month, items in sorted(monthly.items())
        },
        "evaluations": evaluated,
        "caveat": "Historical association is not a forecast. Include delisted/rugged tokens and realistic execution costs; this script does not infer missing forward returns.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Backtest fee.json scoring against supplied forward-return CSV data")
    parser.add_argument("--input", required=True, help="CSV snapshots and forward returns")
    parser.add_argument("--output", help="Write JSON report to this path (default: stdout)")
    parser.add_argument("--config", help="Scoring JSON config (default: fee.json)")
    parser.add_argument("--return-column", default="forward_7d_return_pct", help="Precomputed forward-return column")
    parser.add_argument("--positive-return-pct", type=float, default=20.0, help="Return threshold counted as a hit (default: 20)")
    args = parser.parse_args(argv)
    try:
        report = run_backtest(args.input, load_config(args.config), args.return_column, args.positive_return_pct)
        rendered = json.dumps(report, indent=2, ensure_ascii=False)
        if args.output:
            Path(args.output).write_text(rendered + "\n", encoding="utf-8")
        else:
            print(rendered)
    except (OSError, ValueError) as error:
        print(f"backtest error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
