#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from library.pythoncheck import check_python_version
from library.smartmonitor_imgdat import parse_imgdat_file

check_python_version()


def print_human_summary(summary: dict, show_all: bool) -> None:
    print(f"img.dat: {summary['path']}")
    print(f"Slots: {summary['slot_count']} x {summary['slot_size']} bytes")
    print(f"Non-empty records: {len(summary['records'])}")
    records = summary["records"]
    if not show_all:
        records = [record for record in records if not record["record_type_name"].startswith("unknown_")]
    for record in records:
        fields = ", ".join(f"{key}={value}" for key, value in record["fields"].items())
        print(
            f"  - idx={record['index']:03d} off=0x{record['offset']:04x} "
            f"type=0x{record['record_type']:02x} ({record['record_type_name']}): {fields}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect compiled SmartMonitor img.dat record tables."
    )
    parser.add_argument("input", help="Path to img.dat")
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print machine-readable JSON instead of a human summary.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Include currently unknown slot records in the human summary.",
    )
    args = parser.parse_args()

    input_path = Path(args.input).expanduser()
    if not input_path.is_file():
        raise SystemExit(f"Input file not found: {input_path}")

    parsed = parse_imgdat_file(input_path)
    summary = parsed.to_dict()
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print_human_summary(summary, show_all=args.all)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
