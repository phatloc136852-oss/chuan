"""Command-line interface for scoring one offline token snapshot."""

import argparse
import json
import sys
from pathlib import Path

from chuan.scorer import evaluate_token, load_config


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Score a Solana token snapshot using fee.json")
    parser.add_argument("--input", required=True, help="JSON file with one snapshot, or - to read stdin")
    parser.add_argument("--config", help="Scoring JSON config (default: fee.json in repo/current directory)")
    args = parser.parse_args(argv)
    try:
        raw = sys.stdin.read() if args.input == "-" else Path(args.input).read_text(encoding="utf-8")
        metrics = json.loads(raw)
        result = evaluate_token(metrics, load_config(args.config))
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
