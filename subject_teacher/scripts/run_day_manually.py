"""Manually run one day of subject attendance sync into NEIS."""
from __future__ import annotations

import argparse
import logging
import sys

from subject_teacher.app_service import prepare_run_context, run_day


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="YYYY-MM-DD")
    parser.add_argument("--region", help="교육청 이름 override (예: 경기)")
    parser.add_argument("--neis-password", required=True)
    parser.add_argument("--close", action="store_true", help="출결마감까지 자동 실행")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    context = prepare_run_context(args.date, region_override=args.region)
    print(f"slots to process on {args.date}: {[slot.id for slot, _ in context.day_input.slots]}")
    results = run_day(
        date_str=args.date,
        password=args.neis_password,
        close_after=args.close,
        region_override=args.region,
    )

    ok = sum(1 for result in results if result.status == "ok")
    skipped = sum(1 for result in results if result.status == "skipped")
    failed = [result for result in results if result.status == "failed"]
    print(f"OK={ok} SKIPPED={skipped} FAILED={len(failed)}")
    for result in failed:
        print(f"  - {result.slot_id}: {result.error}")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
