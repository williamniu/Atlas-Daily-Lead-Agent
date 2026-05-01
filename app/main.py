"""CLI entry point for the Atlas Daily Lead Agent."""

import argparse

from app.services.pipeline import print_top_leads, run_pipeline


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="Run the Atlas Daily Lead Agent pipeline.")
    parser.add_argument("--mock", action="store_true", help="Use local mock posts instead of the X API.")
    parser.add_argument("--prod", action="store_true", help="Run in production mode and prefer live collectors.")
    parser.add_argument("--export", action="store_true", help="Export CSV and markdown reports.")
    parser.add_argument("--limit", type=int, default=None, help="Limit the number of posts processed.")
    return parser.parse_args()


def run() -> None:
    """Run the daily lead intelligence workflow."""
    args = parse_args()
    result = run_pipeline(
        use_mock=args.mock,
        export=args.export,
        limit=args.limit,
        prod=args.prod,
    )

    print(f"Run ID: {result.run_id}")
    print(f"Used mock data: {result.used_mock_data}")
    print(f"Raw posts: {len(result.raw_posts)}")
    print(f"Leads: {len(result.leads)}")
    if result.notes:
        print(f"Notes: {result.notes}")
    print_top_leads(result.leads, limit=10)


if __name__ == "__main__":
    run()
