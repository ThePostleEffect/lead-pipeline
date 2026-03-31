"""CLI entrypoint for the lead pipeline.

Usage:
    python -m app.main collect --lane bankruptcy --limit 25 --format json
    python -m app.main collect --lane capital_seeking --limit 25 --min-quality mid_level --format json
    python -m app.main collect --lane charged_off --format json --discards data/output/discards.json
    python -m app.main summarize --input data/output/leads.json --top 10
    python -m app.main export --input data/output/leads.json --xlsx data/output/leads.xlsx
    python -m app.main inspect --input data/output/leads.json --lead-id LEAD-ABC123
    python -m app.main rules
"""

from __future__ import annotations

from dotenv import load_dotenv
load_dotenv()

import argparse
import sys
from pathlib import Path

from app.logging_utils import setup_logging


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lead-pipeline",
        description="Private-company lead discovery, enrichment, filtering, scoring, and export.",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable debug logging")

    sub = parser.add_subparsers(dest="command", help="Available commands")

    # ── collect ──────────────────────────────────────────────────────
    p_collect = sub.add_parser("collect", help="Collect leads for a lane")
    p_collect.add_argument("--lane", required=True, choices=["charged_off", "bankruptcy", "performing", "capital_seeking"])
    p_collect.add_argument("--limit", type=int, default=None, help="Max leads to return")
    p_collect.add_argument("--min-quality", choices=["best_case", "mid_level"], default=None, help="Minimum quality tier")
    p_collect.add_argument("--format", dest="fmt", choices=["json", "text"], default="json", help="Output format")
    p_collect.add_argument("--source", type=str, default=None, help="Path to input file (JSON or CSV)")
    p_collect.add_argument("--source-type", choices=["json", "csv", "web", "auto"], default=None, help="Source format (auto-detects from extension if omitted; 'web' uses live API sources)")
    p_collect.add_argument("--output", type=str, default=None, help="Path to save output JSON")
    p_collect.add_argument("--discards", type=str, default=None, help="Path to save discarded leads JSON")
    p_collect.add_argument("--chapters", type=str, default=None, help="Comma-separated bankruptcy chapters to target (e.g. '13,7')")
    p_collect.add_argument("--lookback-days", type=int, default=None, help="How many days back to search (default: 30)")
    p_collect.add_argument("--include-individuals", action="store_true", default=None, help="Include Ch.13 individual filers with business signals")
    p_collect.add_argument("--no-individuals", action="store_true", default=False, help="Exclude individual filers (business entities only)")
    p_collect.add_argument("--company-types", type=str, default=None, help="Comma-separated company type filters (e.g. 'credit_extenders,auto_dealers')")

    # ── filter ───────────────────────────────────────────────────────
    p_filter = sub.add_parser("filter", help="Filter existing leads")
    p_filter.add_argument("--input", required=True, type=str, help="Path to leads JSON")
    p_filter.add_argument("--lane", type=str, default=None)
    p_filter.add_argument("--state", type=str, default=None)
    p_filter.add_argument("--min-quality", choices=["best_case", "mid_level"], default=None)
    p_filter.add_argument("--min-confidence", type=float, default=None)
    p_filter.add_argument("--private-only", action="store_true")

    # ── rank ─────────────────────────────────────────────────────────
    p_rank = sub.add_parser("rank", help="Rank leads by quality and confidence")
    p_rank.add_argument("--input", required=True, type=str, help="Path to leads JSON")

    # ── summarize ────────────────────────────────────────────────────
    p_summarize = sub.add_parser("summarize", help="Print compact lead summary")
    p_summarize.add_argument("--input", required=True, type=str, help="Path to leads JSON")
    p_summarize.add_argument("--top", type=int, default=None, help="Show only top N leads")

    # ── export ───────────────────────────────────────────────────────
    p_export = sub.add_parser("export", help="Export leads to Excel workbook")
    p_export.add_argument("--input", required=True, type=str, help="Path to leads JSON")
    p_export.add_argument("--xlsx", required=True, type=str, help="Output .xlsx path")

    # ── inspect ──────────────────────────────────────────────────────
    p_inspect = sub.add_parser("inspect", help="Deep-inspect a single lead by ID")
    p_inspect.add_argument("--input", required=True, type=str, help="Path to leads JSON")
    p_inspect.add_argument("--lead-id", required=True, type=str, help="Lead ID to inspect")

    # ── rules ────────────────────────────────────────────────────────
    sub.add_parser("rules", help="Print current pipeline rules")

    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    setup_logging(verbose=args.verbose)

    if args.command == "collect":
        from app.commands.collect import run_collect
        from app.models import SearchFilters

        # Build search filters from CLI flags
        filter_kwargs: dict = {}
        if args.chapters:
            filter_kwargs["chapters"] = [c.strip() for c in args.chapters.split(",")]
        if args.lookback_days is not None:
            filter_kwargs["lookback_days"] = args.lookback_days
        if args.no_individuals:
            filter_kwargs["include_individuals"] = False
        elif args.include_individuals:
            filter_kwargs["include_individuals"] = True
        if args.company_types:
            filter_kwargs["company_types"] = [t.strip() for t in args.company_types.split(",")]
        search_filters = SearchFilters(**filter_kwargs) if filter_kwargs else None

        run_collect(
            lane=args.lane,
            limit=args.limit,
            min_quality=args.min_quality,
            fmt=args.fmt,
            source_file=Path(args.source) if args.source else None,
            source_type=args.source_type,
            output_file=Path(args.output) if args.output else None,
            discards_file=Path(args.discards) if args.discards else None,
            search_filters=search_filters,
        )

    elif args.command == "filter":
        from app.commands.filter import run_filter
        run_filter(
            input_path=Path(args.input),
            lane=args.lane,
            state=args.state,
            min_quality=args.min_quality,
            min_confidence=args.min_confidence,
            private_only=args.private_only,
        )

    elif args.command == "rank":
        from app.commands.rank import run_rank
        run_rank(input_path=Path(args.input))

    elif args.command == "summarize":
        from app.commands.summarize import run_summarize
        run_summarize(input_path=Path(args.input), top=args.top)

    elif args.command == "export":
        from app.commands.export import run_export
        run_export(input_path=Path(args.input), xlsx_path=Path(args.xlsx))

    elif args.command == "inspect":
        from app.commands.inspect import run_inspect
        run_inspect(input_path=Path(args.input), lead_id=args.lead_id)

    elif args.command == "rules":
        from app.commands.rules_cmd import run_rules
        run_rules()


if __name__ == "__main__":
    main()
